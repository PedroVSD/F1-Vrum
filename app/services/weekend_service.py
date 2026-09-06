"""
Orquestrador: ingest -> LLM -> notify
"""

from app.core.config import get_settings
from app.repositories.espn_provider import EspnProvider
from app.repositories.globo_provider import GloboProvider
from app.repositories.openf1_provider import OpenF1Provider
from app.repositories.weekend_provider import JolpicaProvider, build_raw_message
from app.schemas.weekend import NotifyRequest, NotifyResponse, WeekendInfo
from app.services.llm_service import OllamaClient
from app.services.notify_service import EmailNotifier, TelegramNotifier


def get_provider(name: str | None = None):
    s = get_settings()
    provider_name = (name or s.weekend_provider or "jolpica").lower().strip()
    # suporte a lista "jolpica,espn" — pega primeiro para compatibilidade
    provider_name = provider_name.split(",")[0].strip()
    if provider_name in ("all", "multi", "todos"):
        return get_providers("jolpica,espn,globo,openf1")[0]
    if provider_name in ("espn", "espn_provider", "espn_standings", "espn_news"):
        return EspnProvider(
            classificacao_url=s.espn_classificacao_url,
            f1_url=s.espn_f1_url,
        )
    if provider_name in ("openf1", "open_f1"):
        return OpenF1Provider(base_url=s.openf1_base_url)
    if provider_name in ("globo", "ge", "ge.globo", "globo_provider"):
        return GloboProvider(home_url=s.globo_home_url, calendario_url=s.globo_calendario_url)
    # default jolpica + aliases
    return JolpicaProvider(base_url=s.jolpica_base_url)


def get_providers(names: str | None = None) -> list:
    """Retorna lista de providers para síntese multi-fonte."""
    s = get_settings()
    raw = (names or s.weekend_provider or "jolpica").lower().strip()
    if raw in ("all", "multi", "todos"):
        raw = "jolpica,espn,globo,openf1"
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        parts = ["jolpica"]
    providers = []
    for p in parts:
        if p in ("espn", "espn_provider", "espn_standings", "espn_news"):
            providers.append(EspnProvider(classificacao_url=s.espn_classificacao_url, f1_url=s.espn_f1_url))
        elif p in ("openf1", "open_f1"):
            providers.append(OpenF1Provider(base_url=s.openf1_base_url))
        elif p in ("globo", "ge", "ge.globo", "globo_provider"):
            providers.append(GloboProvider(home_url=s.globo_home_url, calendario_url=s.globo_calendario_url))
        else:
            providers.append(JolpicaProvider(base_url=s.jolpica_base_url))
    return providers


def _label_for(provider) -> str:
    name = provider.__class__.__name__.replace("Provider", "")
    mapping = {"Jolpica": "Jolpica (Ergast)", "Espn": "ESPN Brasil", "OpenF1": "OpenF1 Live", "Globo": "ge.globo", "Ge": "ge.globo"}
    return mapping.get(name, name)


async def build_multi_source_raw(session_type, year: str | None, round_: str | None, providers: list) -> tuple[str, WeekendInfo]:
    """Busca cada provider em paralelo e concatena blocos para a LLM sintetizar."""
    import asyncio

    async def fetch_one(p):
        try:
            if year and round_:
                wk = await p.get_weekend(year, round_)
                yr, rd = year, round_
            else:
                wk = await p.get_next_weekend()
                yr, rd = wk.season, wk.round
            results = await p.get_session_results(yr, rd, session_type)
            raw = build_raw_message(wk, session_type, results)
            return wk, raw, None
        except Exception as e:
            return None, f"[{_label_for(p)}] erro: {e}", str(e)

    results = await asyncio.gather(*[fetch_one(p) for p in providers])
    # usa weekend do primeiro que sucedeu como principal
    main_weekend = next((wk for wk, _, err in results if wk is not None), None)
    if not main_weekend:
        # fallback genérico
        from app.schemas.weekend import WeekendInfo
        main_weekend = WeekendInfo(season=year or "2026", round=round_ or "?", race_name="F1 Weekend", circuit_name="", locality="", country="", date="", sessions={})

    blocks = []
    for (wk, raw, err), p in zip(results, providers):
        label = _label_for(p)
        if err:
            blocks.append(f"--- {label} ---\n{raw}")
        else:
            blocks.append(f"--- {label} ---\n{raw}")

    header = f"📦 SÍNTESE MULTI-FONTE ({', '.join(_label_for(p) for p in providers)}) — {len(blocks)} fontes\n"
    header += "Instrução para LLM: sintetize em UMA mensagem única, coerente, em PT-BR, combinando horários/resultados/notícias. Priorize fatos concordantes, cite divergências se houver. Não invente.\n\n"
    combined = header + "\n\n".join(blocks)
    return combined, main_weekend


async def process_weekend(request: NotifyRequest) -> NotifyResponse:
    settings = get_settings()
    is_multi = False
    raw_provider = request.provider or settings.weekend_provider or "jolpica"
    # detecta multi-fonte: "all" ou lista com vírgula
    if raw_provider and ("," in raw_provider or raw_provider.strip().lower() in ("all", "multi", "todos")):
        is_multi = True

    if is_multi:
        providers = get_providers(raw_provider)
        # year/round se passados, usa para todos; senão resolve dentro de build_multi
        raw_message, weekend = await build_multi_source_raw(request.session_type, request.year, request.round, providers)
        # contexto extra para LLM
        multi_context = f"Síntese de {len(providers)} fontes: {', '.join(_label_for(p) for p in providers)}. Combine horários, classificação e notícias."
    else:
        provider = get_provider(raw_provider)
        if request.year and request.round:
            year, round_ = request.year, request.round
            weekend = await provider.get_weekend(year, round_)
        else:
            weekend = await provider.get_next_weekend()
            year, round_ = weekend.season, weekend.round
        results = await provider.get_session_results(year, round_, request.session_type)
        raw_message = build_raw_message(weekend, request.session_type, results)
        multi_context = None

    llm_used = False
    fallback = True
    enhanced = raw_message
    if request.force_llm:
        client = OllamaClient()
        # se multi-fonte, passa contexto para LLM sintetizar
        ctx = multi_context if is_multi else None
        enhanced, fallback, _ = await client.enhance(raw_message, context=ctx)
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
