"""
Orquestrador: ingest -> LLM -> notify
"""

from app.core.config import get_settings
from app.repositories.weekend_provider import JolpicaProvider, build_raw_message
from app.schemas.weekend import NotifyRequest, NotifyResponse, WeekendInfo
from app.services.llm_service import OllamaClient
from app.services.notify_service import EmailNotifier, TelegramNotifier


async def process_weekend(request: NotifyRequest) -> NotifyResponse:
    settings = get_settings()
    provider = JolpicaProvider(base_url=settings.jolpica_base_url)

    if request.year and request.round:
        year, round_ = request.year, request.round
        weekend = await provider.get_weekend(year, round_)
    else:
        weekend = await provider.get_next_weekend()
        year, round_ = weekend.season, weekend.round

    results = await provider.get_session_results(year, round_, request.session_type)
    raw_message = build_raw_message(weekend, request.session_type, results)

    llm_used = False
    fallback = True
    enhanced = raw_message
    if request.force_llm:
        client = OllamaClient()
        enhanced, fallback, _ = await client.enhance(raw_message)
        llm_used = not fallback
    else:
        enhanced = raw_message

    dispatched: dict = {"email": None, "telegram": None, "reasons": {}}

    if request.dry_run:
        dispatched["reasons"]["dry_run"] = "dry_run=true, nenhum envio realizado"
    else:
        channels = request.channels or ["email", "telegram"]
        if "email" in channels:
            notifier = EmailNotifier()
            if notifier.is_configured():
                subject = f"[F1] {weekend.race_name} - {request.session_type.value}"
                ok, msg = notifier.send(subject, enhanced)
                dispatched["email"] = ok
                dispatched["reasons"]["email"] = msg
            else:
                dispatched["email"] = False
                dispatched["reasons"]["email"] = "SMTP não configurado"
        if "telegram" in channels:
            notifier = TelegramNotifier()
            if notifier.is_configured():
                ok, msg = await notifier.send(enhanced)
                dispatched["telegram"] = ok
                dispatched["reasons"]["telegram"] = msg
            else:
                dispatched["telegram"] = False
                dispatched["reasons"]["telegram"] = "Telegram não configurado"

    return NotifyResponse(
        weekend=weekend,
        session_type=request.session_type,
        raw_message=raw_message,
        enhanced_message=enhanced,
        llm_used=llm_used,
        dispatched=dispatched,
    )


async def get_next_weekend_info() -> WeekendInfo:
    s = get_settings()
    provider = JolpicaProvider(base_url=s.jolpica_base_url)
    return await provider.get_next_weekend()


async def get_schedule() -> list[WeekendInfo]:
    s = get_settings()
    provider = JolpicaProvider(base_url=s.jolpica_base_url)
    return await provider.get_current_schedule()
