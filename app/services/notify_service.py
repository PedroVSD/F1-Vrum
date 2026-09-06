"""
Notificadores: Email (SMTP) e Telegram (Bot API).

Ambos são opcionais e lidos via variáveis de ambiente.
Se não configurados, o dispatch apenas reporta skip.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import re

import httpx

from app.core.config import get_settings

TELEGRAM_TIMEOUT = 15.0


def _escape_markdownv2(text: str) -> str:
    """Escapa caracteres reservados do MarkdownV2 fora de entidades formatadas."""
    # Telegram MarkdownV2: _ * [ ] ( ) ~ ` > # + - = | { } . !
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)


def _markdown_to_telegram_markdownv2(text: str) -> str:
    """
    Converte markdown padrão da LLM (**negrito**, *lista, `code`, [link](url))
    para MarkdownV2 do Telegram (*negrito*, _italico_, etc) com escaping correto.
    """
    # Remove separadores --- do LLM
    text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE)

    # 1) Extrai e converte **bold** -> *bold* (MarkdownV2 usa * para negrito)
    bolds: dict[str, str] = {}
    bold_idx = 0

    def repl_bold(m: re.Match) -> str:
        nonlocal bold_idx
        inner = _escape_markdownv2(m.group(1))
        placeholder = f"ZZBOLD{bold_idx}ZZ"
        bolds[placeholder] = f"*{inner}*"
        bold_idx += 1
        return placeholder

    text = re.sub(r"\*\*(.+?)\*\*", repl_bold, text)

    # 2) Extrai `code` -> `code` (já é igual no V2, só escapa conteúdo interno)
    codes: dict[str, str] = {}
    code_idx = 0

    def repl_code(m: re.Match) -> str:
        nonlocal code_idx
        inner = m.group(1)  # code não escapa dentro de crases, mas escapa crase
        placeholder = f"ZZCODE{code_idx}ZZ"
        codes[placeholder] = f"`{inner}`"
        code_idx += 1
        return placeholder

    text = re.sub(r"`(.+?)`", repl_code, text)

    # 3) Links [texto](url) -> [texto](url) (V2 igual, escapa texto)
    links: dict[str, str] = {}
    link_idx = 0

    def repl_link(m: re.Match) -> str:
        nonlocal link_idx
        label = _escape_markdownv2(m.group(1))
        url = m.group(2)
        placeholder = f"ZZLINK{link_idx}ZZ"
        links[placeholder] = f"[{label}]({url})"
        link_idx += 1
        return placeholder

    text = re.sub(r"\[(.+?)\]\((.+?)\)", repl_link, text)

    # 4) Escapa o restante
    text = _escape_markdownv2(text)

    # 5) Listas "*   item" do LLM viraram "\*   item" após escape -> converte para "• "
    text = re.sub(r"^\\\*(\s+)", "• ", text, flags=re.MULTILINE)

    # 6) Restaura placeholders (já escapados)
    for ph, val in bolds.items():
        text = text.replace(ph, val)
    for ph, val in codes.items():
        text = text.replace(ph, val)
    for ph, val in links.items():
        text = text.replace(ph, val)

    # 7) Limpa linhas vazias duplicadas deixadas pelo ---
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_markdown(text: str) -> str:
    """Remove símbolos markdown para fallback plain-text."""
    plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    plain = re.sub(r"`(.+?)`", r"\1", plain)
    plain = re.sub(r"^\s*---\s*$", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^\*\s+", "• ", plain, flags=re.MULTILINE)
    plain = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", plain)
    return plain


class EmailNotifier:
    def __init__(self):
        s = get_settings()
        self.host = s.smtp_host
        self.port = s.smtp_port
        self.user = s.smtp_user
        self.password = s.smtp_password
        self.from_addr = s.smtp_from or s.smtp_user
        self.to_addrs = [x.strip() for x in (s.smtp_to or "").split(",") if x.strip()]
        self.use_tls = s.smtp_use_tls

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password and self.to_addrs)

    def send(self, subject: str, body: str) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "SMTP não configurado (ver .env)"
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_addr or ""
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            html = body.replace("\n", "<br>")
            msg.attach(MIMEText(f"<html><body><pre>{html}</pre></body></html>", "html", "utf-8"))

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
            return True, f"Enviado para {', '.join(self.to_addrs)}"
        except Exception as e:
            return False, f"Falha SMTP: {e}"


class TelegramNotifier:
    def __init__(self):
        s = get_settings()
        self.token = s.telegram_bot_token
        self.chat_ids = [x.strip() for x in (s.telegram_chat_id or "").split(",") if x.strip()]

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_ids)

    async def send(self, text: str) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "Telegram não configurado (BOT_TOKEN / CHAT_ID)"
        # Converte markdown padrão (**bold**) para MarkdownV2 do Telegram (*bold*)
        md_text = _markdown_to_telegram_markdownv2(text)
        plain_text = _strip_markdown(text)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        ok_count = 0
        errors = []
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
            for chat_id in self.chat_ids:
                try:
                    # 1) Tenta MarkdownV2 (markdown renderizado)
                    resp = await client.post(
                        url, json={"chat_id": chat_id, "text": md_text, "parse_mode": "MarkdownV2"}
                    )
                    if resp.status_code == 200:
                        ok_count += 1
                        continue
                    # 2) Fallback: MarkdownV2 falhou (ex: escaping), tenta sem parse_mode com texto limpo
                    resp2 = await client.post(url, json={"chat_id": chat_id, "text": plain_text})
                    if resp2.status_code == 200:
                        ok_count += 1
                    else:
                        errors.append(f"{chat_id}: {resp.text[:200]}")
                except Exception as e:
                    errors.append(f"{chat_id}: {e}")
        if ok_count == len(self.chat_ids):
            return True, f"Enviado para {ok_count} chat(s)"
        if ok_count > 0:
            return True, f"Parcial: {ok_count}/{len(self.chat_ids)} - {'; '.join(errors)}"
        return False, "; ".join(errors) or "Falha desconhecida"

    def send_sync(self, text: str) -> tuple[bool, str]:
        import asyncio

        return asyncio.run(self.send(text))
