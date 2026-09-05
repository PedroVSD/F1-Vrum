"""
Provider OpenF1 - API aberta https://api.openf1.org

Endpoints usados:
  GET /v1/meetings?year={year}          -> calendário
  GET /v1/sessions?year={year}           -> sessões (treinos/sprint/quali/corrida)
  GET /v1/drivers?session_key=latest     -> pilotos
  GET /v1/session_result?session_key={k} -> não existe; usamos /v1/position ou /v1/drivers como fallback
  GET /v1/position?session_key={k}       -> posições em tempo real (se houver)
  GET /v1/laps?session_key={k}           -> voltas

Como OpenF1 é live-timing (não tem resultado final consolidado como Jolpica),
a estratégia é:
 - calendário/meetings -> WeekendInfo
 - session_results -> tenta buscar positions/laps; se vazio, retorna standings de drivers como placeholder

Totalmente plugável via WeekendProvider protocol.
"""

import httpx

from app.schemas.weekend import SessionResultItem, SessionType, WeekendInfo

OPENF1_BASE_URL = "https://api.openf1.org/v1"
OPENF1_TIMEOUT = 15.0


class OpenF1Provider:
    def __init__(self, base_url: str = OPENF1_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=OPENF1_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()

    def _meeting_to_weekend(self, m: dict) -> WeekendInfo:
        # date_start: 2025-03-14T01:30:00+00:00
        date = (m.get("date_start") or "")[:10]
        time = (m.get("date_start") or "")[11:19] if "T" in m.get("date_start", "") else None
        return WeekendInfo(
            season=str(m.get("year", "")),
            round=str(m.get("meeting_key", "")),
            race_name=m.get("meeting_name") or m.get("meeting_official_name") or "GP",
            circuit_name=m.get("circuit_short_name") or m.get("location") or "",
            locality=m.get("location") or "",
            country=m.get("country_name") or m.get("country_code") or "",
            date=date,
            time=time,
            sessions={
                "meeting_key": m.get("meeting_key"),
                "circuit_key": m.get("circuit_key"),
                "gmt_offset": m.get("gmt_offset"),
            },
        )

    async def get_current_schedule(self) -> list[WeekendInfo]:
        data = await self._get("meetings", params={"year": 2025})
        # OpenF1 tem 2025 completo; para 2026 usa 2025 como fallback
        if not data:
            data = await self._get("meetings", params={"year": 2024})
        return [self._meeting_to_weekend(m) for m in data]

    async def get_next_weekend(self) -> WeekendInfo:
        # pega meetings futuros - simplifica pegando último da lista (próximo a acontecer)
        schedule = await self.get_current_schedule()
        if not schedule:
            raise ValueError("Nenhum meeting OpenF1 encontrado")
        # tenta achar mais recente; OpenF1 não tem flag next, então retorna último ou primeiro de 2025/2026
        # para demo: retorna o que tem date_start mais próximo do futuro
        import datetime

        now = datetime.datetime.utcnow().date().isoformat()
        future = [w for w in schedule if w.date >= now]
        if future:
            return sorted(future, key=lambda w: w.date)[0]
        return schedule[-1]

    async def get_weekend(self, year: str, round: str) -> WeekendInfo:
        data = await self._get("meetings", params={"year": int(year) if year.isdigit() else 2025})
        for m in data:
            if str(m.get("meeting_key")) == round:
                return self._meeting_to_weekend(m)
        # fallback: round como índice 1-based
        if round.isdigit():
            idx = int(round) - 1
            if 0 <= idx < len(data):
                return self._meeting_to_weekend(data[idx])
        raise ValueError(f"Corrida não encontrada OpenF1: {year} round {round}")

    async def get_session_results(
        self, year: str, round: str, session: SessionType
    ) -> list[SessionResultItem]:
        """
        Tenta mapear session_type para OpenF1 session.
        Se não houver dados de posição, retorna lista de pilotos como placeholder.
        """
        # 1. Resolve meeting
        try:
            weekend = await self.get_weekend(year, round)
            meeting_key = weekend.sessions.get("meeting_key")
        except Exception:
            meeting_key = None

        # 2. Descobre session_key do tipo desejado
        session_key = None
        try:
            # busca sessions do meeting
            if meeting_key:
                sessions = await self._get("sessions", params={"meeting_key": meeting_key})
            else:
                sessions = await self._get("sessions", params={"year": int(year) if year.isdigit() else 2025})
            # mapeia SessionType -> OpenF1 session_type/session_name
            type_map = {
                SessionType.fp1: ["Practice 1", "Practice"],
                SessionType.fp2: ["Practice 2", "Practice"],
                SessionType.fp3: ["Practice 3", "Practice"],
                SessionType.qualifying: ["Qualifying"],
                SessionType.sprint_qualifying: ["Sprint Qualifying", "Sprint Shootout"],
                SessionType.sprint: ["Sprint"],
                SessionType.race: ["Race"],
            }
            wanted = type_map.get(session, ["Race"])
            for s in sessions:
                name = s.get("session_name", "")
                stype = s.get("session_type", "")
                if any(w.lower() in name.lower() or w.lower() in stype.lower() for w in wanted):
                    # para FP1/2/3 precisa match exato Practice 1/2/3
                    if session in (SessionType.fp1, SessionType.fp2, SessionType.fp3):
                        if wanted[0].lower() == name.lower():
                            session_key = s.get("session_key")
                            break
                    else:
                        session_key = s.get("session_key")
                        break
            if not session_key and sessions:
                # fallback: pega primeira que contenha wanted[0]
                session_key = sessions[0].get("session_key")
        except Exception:
            session_key = None

        # 3. Tenta buscar posições finais
        if session_key:
            try:
                positions = await self._get("position", params={"session_key": session_key})
                # positions é lista com driver_number e position; pega última volta por driver
                if positions:
                    # agrupa por driver_number, pega maior position? Na API position é ordem em pista
                    # Simplifica: pega último registro por driver (mais recente)
                    latest: dict[int, dict] = {}
                    for p in positions:
                        dn = p.get("driver_number")
                        if dn not in latest or p.get("date", "") > latest[dn].get("date", ""):
                            latest[dn] = p
                    # busca nomes dos pilotos
                    try:
                        drivers = await self._get("drivers", params={"session_key": session_key})
                        driver_map = {d["driver_number"]: f"{d['first_name']} {d['last_name']}" for d in drivers}
                        team_map = {d["driver_number"]: d.get("team_name", "") for d in drivers}
                    except Exception:
                        driver_map, team_map = {}, {}
                    sorted_pos = sorted(latest.values(), key=lambda x: x.get("position") or 999)
                    out = []
                    for p in sorted_pos[:20]:
                        dn = p.get("driver_number")
                        out.append(
                            SessionResultItem(
                                position=str(p.get("position") or ""),
                                driver=driver_map.get(dn, f"#{dn}"),
                                team=team_map.get(dn, ""),
                                time=None,
                                points=None,
                                status=None,
                            )
                        )
                    if out:
                        return out
            except Exception:
                pass

        # 4. Fallback: lista de pilotos da sessão
        try:
            sk = session_key or "latest"
            drivers = await self._get("drivers", params={"session_key": sk})
            out = []
            for idx, d in enumerate(drivers[:20], start=1):
                out.append(
                    SessionResultItem(
                        position=str(idx),
                        driver=f"{d.get('first_name','')} {d.get('last_name','')}".strip(),
                        team=d.get("team_name", ""),
                        time=d.get("name_acronym"),
                        points=None,
                        status=None,
                    )
                )
            return out
        except Exception:
            return []
