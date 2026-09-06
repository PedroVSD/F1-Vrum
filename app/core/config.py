from functools import lru_cache

from pydantic_settings import BaseSettings


class WeekendSettings(BaseSettings):
    # --- Fonte de dados (sites de esporte / APIs) ---
    # Provedor padrão: Jolpica (Ergast successor) - gratuito, sem API key
    # Alternativas: espn (scraping), openf1 (live timing)
    # Seleção via env WEEKEND_PROVIDER ou campo provider na request
    weekend_provider: str = "jolpica"
    jolpica_base_url: str = "https://api.jolpi.ca/ergast/f1"
    espn_classificacao_url: str = "https://www.espn.com.br/f1/classificacao"
    espn_f1_url: str = "https://www.espn.com.br/f1/"
    openf1_base_url: str = "https://api.openf1.org/v1"
    globo_home_url: str = "https://ge.globo.com/motor/formula-1/"
    globo_calendario_url: str = "https://ge.globo.com/motor/formula-1/noticia/2026/03/14/f1-2026-veja-como-fica-calendario-sem-gps-do-bahrein-e-arabia-saudita.ghtml"

    # --- Ollama Cloud ---
    ollama_api_key: str | None = None
    ollama_model: str = "gemma4:31b-cloud"
    ollama_base_url: str = "https://ollama.com"
    # Prompt base para edição da mensagem
    ollama_system_prompt: str = (
        "Você é um editor experiente de notícias de Fórmula 1. "
        "Receba um texto bruto com resultados/horários de uma sessão do fim de semana de corrida "
        "(treino, sprint, qualificação, corrida e atual estado do campeonato, pontos dos pilotos) Você também deve dar uma atenção especial para certos pilotos, como Max Verstappen, Chalers Leclerc, Lando Noris, Oscar Piatri, Gabriel Bortoletto e Kimi Antonelli. E caso tenha algum acontecimento na pista, também deve ser informado .E reescreva de forma clara, envolvente e objetiva, "
        "em português do Brasil, mantendo todos os dados factuais (posições, tempos, nomes). "
        "Você deve informar os dados disponíveis no momento em que você recebe, Se foi até o dia da classificação, deve informar os dados dos treinos livres(apenas como foi, o top três de cada um) e posteriormente os dados da classificação. No dia da corrida, informar como foram os dados da classificação e como terminou a corrida. Claro tendo algum aconteceimento, ele deve ser informado também."
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
    telegram_chat_id: str | None = (
        None  # id ou @canal, separado por vírgula para múltiplos
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def has_email_config(self) -> bool:
        return bool(
            self.smtp_host and self.smtp_user and self.smtp_password and self.smtp_to
        )

    def has_telegram_config(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def has_ollama_config(self) -> bool:
        return bool(self.ollama_api_key)


@lru_cache
def get_settings() -> WeekendSettings:
    return WeekendSettings()  # type: ignore
