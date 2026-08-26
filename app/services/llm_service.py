"""
Cliente Ollama Cloud para edição/polimento da mensagem do fim de semana.

API: https://ollama.com/docs/api  (Ollama Cloud)
  POST {base_url}/api/chat
  Headers: Authorization: Bearer <OLLAMA_API_KEY>
  Body: { model, messages: [{role, content}], stream: false }

Fallback: se sem API key ou falha, retorna a mensagem bruta.
"""

import httpx

from app.core.config import get_settings

TIMEOUT = 30.0


class OllamaClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        system_prompt: str | None = None,
    ):
        s = get_settings()
        self.api_key = api_key or s.ollama_api_key
        self.model = model or s.ollama_model
        self.base_url = (base_url or s.ollama_base_url).rstrip("/")
        self.system_prompt = system_prompt or s.ollama_system_prompt

    async def enhance(self, raw_message: str, context: str | None = None) -> tuple[str, bool, str | None]:
        """
        Retorna (mensagem_editada, fallback_used, model_usado)
        Se fallback_used=True, a mensagem é a original.
        """
        if not self.api_key:
            return raw_message, True, None

        user_prompt = raw_message
        if context:
            user_prompt = f"Contexto: {context}\n\nDados brutos:\n{raw_message}"

        user_prompt += (
            "\n\nReescreva a mensagem acima em PT-BR, de forma atraente para envio por e-mail/Telegram. "
            "Mantenha factual. Se resultados estiverem vazios, destaque os horários."
        )

        # Evita duplicar /api/chat se base_url já contém
        base = self.base_url
        if base.endswith("/api/chat"):
            url = base
        elif base.endswith("/api"):
            url = f"{base}/chat"
        else:
            url = f"{base}/api/chat"

        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = None
                if "message" in data and isinstance(data["message"], dict):
                    content = data["message"].get("content")
                elif "response" in data:
                    content = data["response"]
                elif "choices" in data:
                    content = data["choices"][0]["message"]["content"]

                if content and content.strip():
                    return content.strip(), False, self.model
                return raw_message, True, self.model
        except Exception as e:
            print(f"[Ollama] falhou ({e}), usando mensagem bruta")
            return raw_message, True, self.model

    def enhance_sync(self, raw_message: str, context: str | None = None) -> tuple[str, bool, str | None]:
        import asyncio

        return asyncio.run(self.enhance(raw_message, context))
