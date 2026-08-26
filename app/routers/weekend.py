from fastapi import APIRouter, Query

from app.schemas.weekend import NotifyRequest, NotifyResponse, SessionType, WeekendInfo
from app.services.weekend_service import get_next_weekend_info, get_schedule, process_weekend

router = APIRouter(prefix="/weekend", tags=["Weekend - Fim de semana de corrida"])


@router.get("/next", summary="Próximo fim de semana (calendário)", response_model=WeekendInfo)
async def next_weekend():
    """
    Retorna a próxima corrida do calendário (fonte: Jolpica F1 API).
    Útil para saber circuito, data e horários de treinos/sprint/quali/corrida.
    """
    return await get_next_weekend_info()


@router.get("/schedule", summary="Calendário completo da temporada", response_model=list[WeekendInfo])
async def schedule():
    """Calendário completo da temporada atual."""
    return await get_schedule()


@router.get("/preview", summary="Prévia da mensagem (sem LLM/ sem envio)")
async def preview(
    session_type: SessionType = Query(..., description="Sessão: fp1, fp2, fp3, qualifying, sprint, race"),
    year: str | None = Query(None, description="Ano, ex: 2025. Default = temporada atual/próxima corrida"),
    round: str | None = Query(None, description="Rodada, ex: 1. Default = próxima corrida"),
):
    """Gera a mensagem bruta (factual) para uma sessão, sem passar pela LLM e sem notificar."""
    req = NotifyRequest(session_type=session_type, year=year, round=round, dry_run=True, force_llm=False)
    result = await process_weekend(req)
    return {
        "weekend": result.weekend,
        "session_type": result.session_type,
        "raw_message": result.raw_message,
    }


@router.post("/notify", summary="Pipeline completo: ingest -> LLM -> email/telegram", response_model=NotifyResponse)
async def notify(request: NotifyRequest):
    """
    Pipeline completo:

    1. **Ingest**: busca dados da sessão em APIs/sites de esporte (Jolpica F1 por padrão)
    2. **LLM**: envia o texto bruto para Ollama Cloud para reescrita/editar a mensagem (se OLLAMA_API_KEY configurada)
    3. **Notify**: envia por email e/ou Telegram (se SMTP/Telegram configurados)

    - `dry_run=true` -> não envia, só retorna `enhanced_message`
    - `channels` -> filtrar ["email"] ou ["telegram"]
    - `force_llm=false` -> pula LLM
    """
    return await process_weekend(request)


@router.get("/health", summary="Verifica configuração dos canais")
async def health():
    from app.core.config import get_settings

    s = get_settings()
    return {
        "ingest_provider": s.jolpica_base_url,
        "ollama": {
            "configured": s.has_ollama_config(),
            "model": s.ollama_model,
            "base_url": s.ollama_base_url,
        },
        "email": {
            "configured": s.has_email_config(),
            "host": s.smtp_host,
            "to": s.smtp_to,
        },
        "telegram": {
            "configured": s.has_telegram_config(),
            "chat_id": s.telegram_chat_id,
        },
    }
