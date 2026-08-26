"""
Ingestão de dados do fim de semana de corrida.

Fonte principal: Jolpica F1 API (sucessora do Ergast) - https://api.jolpi.ca/ergast/f1
  - Gratuita, sem API key, atualizada
  - Endpoints usados:
    GET /current.json              -> calendário da temporada
    GET /current/next.json         -> próxima corrida
    GET /{year}/{round}/results.json   -> resultado da corrida
    GET /{year}/{round}/qualifying.json -> grid de qualificação
    GET /{year}/{round}/sprint.json     -> resultado sprint

Arquitetura extensível: interface `WeekendProvider` permite adicionar
outros provedores (ex: ESPN scraper, OpenF1) sem mudar o service.
"""

from typing import Protocol

import httpx

from app.schemas.weekend import SessionResultItem, SessionType, WeekendInfo

JOLPICA_TIMEOUT = 15.0


class WeekendProvider(Protocol):
    async def get_next_weekend(self) -> WeekendInfo: ...
    async def get_weekend(self, year: str, round: str) -> WeekendInfo: ...
    async def get_session_results(
        self, year: str, round: str, session: SessionType
    ) -> list[SessionResultItem]: ...


class JolpicaProvider:
    """Provedor baseado na Jolpica API (Ergast)."""

    def __init__(self, base_url: str = "https://api.jolpi.ca/ergast/f1"):
        self.base_url = base_url.rstrip("/")

    async def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=JOLPICA_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()

    def _parse_weekend(self, race: dict) -> WeekendInfo:
        return WeekendInfo(
            season=race.get("season", ""),
            round=race.get("round", ""),
            race_name=race.get("raceName", ""),
            circuit_name=race.get("Circuit", {}).get("circuitName", ""),
            locality=race.get("Circuit", {}).get("Location", {}).get("locality", ""),
            country=race.get("Circuit", {}).get("Location", {}).get("country", ""),
            date=race.get("date", ""),
            time=race.get("time"),
            sessions={
                "FirstPractice": race.get("FirstPractice"),
                "SecondPractice": race.get("SecondPractice"),
                "ThirdPractice": race.get("ThirdPractice"),
                "Qualifying": race.get("Qualifying"),
                "Sprint": race.get("Sprint"),
                "SprintQualifying": race.get("SprintQualifying"),
            },
        )

    async def get_next_weekend(self) -> WeekendInfo:
        data = await self._get("current/next.json")
        race = data["MRData"]["RaceTable"]["Races"][0]
        return self._parse_weekend(race)

    async def get_weekend(self, year: str, round: str) -> WeekendInfo:
        data = await self._get(f"{year}/{round}.json") if round != "next" else await self._get("current/next.json")
        if "MRData" in data and data["MRData"]["RaceTable"]["Races"]:
            race = data["MRData"]["RaceTable"]["Races"][0]
            return self._parse_weekend(race)
        data = await self._get(f"{year}.json")
        for r in data["MRData"]["RaceTable"]["Races"]:
            if r["round"] == round:
                return self._parse_weekend(r)
        raise ValueError(f"Corrida não encontrada: {year} round {round}")

    async def get_current_schedule(self) -> list[WeekendInfo]:
        data = await self._get("current.json")
        return [self._parse_weekend(r) for r in data["MRData"]["RaceTable"]["Races"]]

    async def get_session_results(
        self, year: str, round: str, session: SessionType
    ) -> list[SessionResultItem]:
        endpoint_map = {
            SessionType.race: f"{year}/{round}/results.json",
            SessionType.qualifying: f"{year}/{round}/qualifying.json",
            SessionType.sprint: f"{year}/{round}/sprint.json",
            SessionType.sprint_qualifying: f"{year}/{round}/sprint.json",
            SessionType.fp1: f"{year}/{round}/practice/1.json",
            SessionType.fp2: f"{year}/{round}/practice/2.json",
            SessionType.fp3: f"{year}/{round}/practice/3.json",
        }
        path = endpoint_map.get(session)
        if not path:
            return []

        try:
            data = await self._get(path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

        table = data.get("MRData", {}).get("RaceTable", {})
        races = table.get("Races", [])
        if not races:
            return []
        race = races[0]

        if session == SessionType.qualifying:
            quali = race.get("QualifyingResults", [])
            out = []
            for q in quali:
                driver = f"{q['Driver']['givenName']} {q['Driver']['familyName']}"
                out.append(
                    SessionResultItem(
                        position=q.get("position", ""),
                        driver=driver,
                        team=q.get("Constructor", {}).get("name", ""),
                        time=q.get("Q3") or q.get("Q2") or q.get("Q1"),
                    )
                )
            return out

        if session in (SessionType.race, SessionType.sprint):
            key = "Results" if session == SessionType.race else "SprintResults"
            results = race.get(key) or race.get("Results") or race.get("SprintResults") or []
            out = []
            for r in results:
                driver = f"{r['Driver']['givenName']} {r['Driver']['familyName']}"
                out.append(
                    SessionResultItem(
                        position=r.get("position", ""),
                        driver=driver,
                        team=r.get("Constructor", {}).get("name", ""),
                        time=r.get("Time", {}).get("time") if isinstance(r.get("Time"), dict) else r.get("Time"),
                        points=r.get("points"),
                        status=r.get("status"),
                    )
                )
            return out

        practice = race.get("PracticeResults") or race.get("Results") or []
        out = []
        for p in practice:
            driver = f"{p['Driver']['givenName']} {p['Driver']['familyName']}" if "Driver" in p else p.get("driver", "")
            out.append(
                SessionResultItem(
                    position=p.get("position", ""),
                    driver=driver,
                    team=p.get("Constructor", {}).get("name", ""),
                    time=p.get("Time", {}).get("time") if isinstance(p.get("Time"), dict) else p.get("Time"),
                )
            )
        return out


def build_raw_message(weekend: WeekendInfo, session: SessionType, results: list[SessionResultItem]) -> str:
    """Gera mensagem bruta factual que será enviada à LLM."""
    from app.schemas.weekend import SESSION_LABELS

    label = SESSION_LABELS.get(session, session.value)
    header = (
        f"🏁 {weekend.race_name} - {label}\n"
        f"📍 {weekend.circuit_name} ({weekend.locality}, {weekend.country})\n"
        f"📅 {weekend.date} | Temporada {weekend.season} - Rodada {weekend.round}\n"
    )
    if not results:
        header += "\nResultados ainda não disponíveis. Horários do fim de semana:\n"
        for k, v in weekend.sessions.items():
            if v:
                header += f" - {k}: {v.get('date')} {v.get('time','')}\n"
        return header.strip()

    lines = [header, f"\nResultados - {label}:\n"]
    for r in results[:10]:
        extra = f" | {r.time}" if r.time else ""
        if r.points:
            extra += f" | {r.points} pts"
        if r.status and r.status != "Finished":
            extra += f" | {r.status}"
        lines.append(f"{r.position}. {r.driver} ({r.team}){extra}")

    if len(results) > 10:
        lines.append(f"\n... e mais {len(results)-10} pilotos")

    return "\n".join(lines)
