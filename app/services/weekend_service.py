"""
Orquestrador: ingest -> LLM -> notify
"""

from app.core.config import get_settings
from app.repositories.espn_provider import EspnProvider
from app.repositories.openf1_provider import OpenF1Provider
from app.repositories.weekend_provider import JolpicaProvider, build_raw_message
from app.schemas.weekend import NotifyRequest, NotifyResponse, WeekendInfo
from app.services.llm_service import OllamaClient
from app.services.notify_service import EmailNotifier, TelegramNotifier


def get_provider(name: str | None = None):
    s = get_settings()
    provider_name = (name or s.weekend_provider or "jolpica").lower().strip()
    if provider_name in ("espn", "espn_provider", "espn_standings", "espn_news"):
        return EspnProvider(
            classificacao_url=s.espn_classificacao_url,
            f1_url=s.espn_f1_url,
        )
    if provider_name in ("openf1", "open_f1"):
        return OpenF1Provider(base_url=s.openf1_base_url)
    # default jolpica + aliases
    return JolpicaProvider(base_url=s.jolpica_base_url)


async def process_weekend(request: NotifyRequest) -> NotifyResponse:
    settings = get_settings()
    provider = get_provider(request.provider or settings.weekend_provider)

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


async def get_next_weekend_info(provider_name: str | None = None) -> WeekendInfo:
    provider = get_provider(provider_name)
    return await provider.get_next_weekend()


async def get_schedule(provider_name: str | None = None) -> list[WeekendInfo]:
    provider = get_provider(provider_name)
    return await provider.get_current_schedule()
