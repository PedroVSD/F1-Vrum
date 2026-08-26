from functools import lru_cache

from pydantic_settings import BaseSettings


class WeekendSettings(BaseSettings):
    # --- Fonte de dados (sites de esporte / APIs) ---
    # Provedor padrão: Jolpica (Ergast successor) - gratuito, sem API key
    # Alternativa futura: ESPN scraping, OpenF1
    jolpica_base_url: str = "https://api.jolpi.ca/ergast/f1"

    # --- Ollama Cloud ---
    ollama_api_key: str | None = None
    ollama_model: str = "llama3.1:8b"
    ollama_base_url: str = "https://ollama.com"
    # Prompt base para edição da mensagem
    ollama_system_prompt: str = (
        "Você é um editor experiente de notícias de Fórmula 1. "
        "Receba um texto bruto com resultados/horários de uma sessão do fim de semana de corrida "
        "(treino, sprint, qualificação ou corrida) e reescreva de forma clara, envolvente e objetiva, "
        "em português do Brasil, mantendo todos os dados factuais (posições, tempos, nomes). "
        "Use tom jornalístico leve, com emojis moderados. Não invente dados."
    )

    # --- Email (SMTP) ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None  # lista separada por vírgula
    smtp_use_tls: bool = True

    # --- Telegram ---
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None  # id ou @canal, separado por vírgula para múltiplos

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def has_email_config(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.smtp_to)

    def has_telegram_config(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def has_ollama_config(self) -> bool:
        return bool(self.ollama_api_key)


@lru_cache
def get_settings() -> WeekendSettings:
    return WeekendSettings()  # type: ignore
