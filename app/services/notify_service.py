"""
Notificadores: Email (SMTP) e Telegram (Bot API).

Ambos são opcionais e lidos via variáveis de ambiente.
Se não configurados, o dispatch apenas reporta skip.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.core.config import get_settings

TELEGRAM_TIMEOUT = 15.0


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
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        ok_count = 0
        errors = []
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
            for chat_id in self.chat_ids:
                try:
                    resp = await client.post(
                        url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
                    )
                    if resp.status_code == 200:
                        ok_count += 1
                    else:
                        resp2 = await client.post(url, json={"chat_id": chat_id, "text": text})
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
