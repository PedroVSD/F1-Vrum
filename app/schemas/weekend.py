from enum import Enum

from pydantic import BaseModel, Field


class SessionType(str, Enum):
    fp1 = "fp1"
    fp2 = "fp2"
    fp3 = "fp3"
    qualifying = "qualifying"
    sprint_qualifying = "sprint_qualifying"
    sprint = "sprint"
    race = "race"


# Mapeamento amigável para exibição
SESSION_LABELS: dict[SessionType, str] = {
    SessionType.fp1: "Treino Livre 1",
    SessionType.fp2: "Treino Livre 2",
    SessionType.fp3: "Treino Livre 3",
    SessionType.qualifying: "Qualificação",
    SessionType.sprint_qualifying: "Qualificação Sprint",
    SessionType.sprint: "Sprint",
    SessionType.race: "Corrida",
}


class SessionResultItem(BaseModel):
    position: str
    driver: str  # ex: "Max Verstappen"
    team: str
    time: str | None = None
    points: str | None = None
    status: str | None = None


class WeekendInfo(BaseModel):
    season: str
    round: str
    race_name: str
    circuit_name: str
    locality: str
    country: str
    date: str
    time: str | None = None
    sessions: dict = Field(default_factory=dict)  # horários crus da API


class RawUpdate(BaseModel):
    weekend: WeekendInfo
    session_type: SessionType
    results: list[SessionResultItem] = Field(default_factory=list)
    raw_message: str


class EnhancedUpdate(BaseModel):
    weekend: WeekendInfo
    session_type: SessionType
    raw_message: str
    enhanced_message: str
    llm_model: str | None = None
    fallback_used: bool = False


class NotifyRequest(BaseModel):
    session_type: SessionType = Field(description="Sessão do fim de semana para notificar")
    year: str | None = Field(default=None, description="Ano da temporada, default = atual")
    round: str | None = Field(default=None, description="Rodada, default = próxima corrida")
    dry_run: bool = Field(default=False, description="Se true, não envia email/telegram, só retorna mensagem")
    force_llm: bool = Field(
        default=True, description="Se true, tenta usar Ollama Cloud; se false, usa mensagem bruta"
    )
    channels: list[str] | None = Field(
        default=None, description="Canais: email, telegram. Default = todos configurados"
    )


class NotifyResponse(BaseModel):
    weekend: WeekendInfo
    session_type: SessionType
    raw_message: str
    enhanced_message: str
    llm_used: bool
    dispatched: dict  # ex: {"email": true, "telegram": false, "reasons": {...}}
