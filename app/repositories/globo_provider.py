"""
Provider Globo Esporte - https://ge.globo.com/motor/formula-1/

Usado como:
- Notícias: https://ge.globo.com/motor/formula-1/  -> JSON embutido com posts (títulos)
- Calendário: mesma home + artigo https://ge.globo.com/motor/formula-1/noticia/2026/03/14/f1-2026-veja-como-fica-calendario-sem-gps-do-bahrein-e-arabia-saudita.ghtml -> lista de GPs

Implementa WeekendProvider para ser plugável (provider=globo ou ge).
Para sessões (treinos/sprint/qualificação/corrida) retorna calendário/horários quando disponível,
e notícias como fallback, para a LLM sintetizar.
"""

import re

import httpx

from app.schemas.weekend import SessionResultItem, SessionType, WeekendInfo

GE_HOME_URL = "https://ge.globo.com/motor/formula-1/"
GE_CALENDARIO_URL = "https://ge.globo.com/motor/formula-1/noticia/2026/03/14/f1-2026-veja-como-fica-calendario-sem-gps-do-bahrein-e-arabia-saudita.ghtml"
GE_TIMEOUT = 15.0
HEADERS = {"User-Agent": "Mozilla/5.0 (RaceHub F1 API)"}


class GloboProvider:
    """Scraping leve do ge.globo.com/motor/formula-1/"""

    def __init__(
        self,
        home_url: str = GE_HOME_URL,
        calendario_url: str = GE_CALENDARIO_URL,
    ):
        self.home_url = home_url
        self.calendario_url = calendario_url

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=GE_TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    # ---------- parsing ----------

    def _parse_noticias(self, html: str) -> list[dict]:
        # JSON posts: "title":"Título com 15+ chars"
        titles = re.findall(r'"title":"([^"]{15,150})"', html)
        # filtra ruídos (ex: "F1 2026", "ge.globo")
        filtered = []
        seen = set()
        for t in titles:
            t = t.strip()
            # ge.globo já vem decodificado utf-8; não aplicar unicode_escape (que quebra acentos)
            # apenas tenta decodificar se ainda houver \\u escapes literais
            if "\\u" in t:
                try:
                    t = t.encode("utf-8").decode("unicode_escape")
                except Exception:
                    pass
            if len(t) < 15 or t in seen:
                continue
            low = t.lower()
            if any(x in low for x in ["f1 2026", "ge.globo", "globo.com", "all rights"]):
                continue
            seen.add(t)
            filtered.append(t)
            if len(filtered) >= 15:
                break
        # links para notícias
        links = re.findall(r'"url":"(https://ge\.globo\.com/motor/formula-1/noticia[^"]*)"', html)
        noticias = []
        for i, title in enumerate(filtered[:10]):
            link = links[i] if i < len(links) else ""
            # unescape \/ -> /
            link = link.replace("\\/", "/")
            noticias.append({"title": title, "link": link})
        return noticias

    def _noticias_to_results(self, noticias: list[dict]) -> list[SessionResultItem]:
        out = []
        for idx, n in enumerate(noticias, start=1):
            out.append(
                SessionResultItem(
                    position=str(idx),
                    driver=n["title"][:65],
                    team="ge.globo Notícia",
                    time=n["link"] or None,
                    points=None,
                    status=None,
                )
            )
        return out

    def _parse_calendario(self, html: str, home_html: str | None = None) -> list[WeekendInfo]:
        """Tenta extrair lista de GPs do artigo de calendário + home."""
        weekends: list[WeekendInfo] = []
        # tenta extrair do home JSON: procura "Conheça o calendário" e lista de GPs próximos
        # fallback: procura padrão "GP da ...", "GP de ...", "GP do ..."
        gps = re.findall(r'GP (?:da|de|do) ([A-Za-zÀ-ÿ\s]+)', html)
        # dedup preservando ordem
        seen = set()
        uniq_gps = []
        for g in gps:
            g = g.strip().split("<")[0].split('"')[0].strip()
            # remove sufixos como " de Fórmula 1 2026"
            g = re.sub(r'\s+de Fórmula 1.*', '', g)
            g = g.strip()
            if len(g) < 3 or len(g) > 30:
                continue
            key = g.lower()
            if key not in seen:
                seen.add(key)
                uniq_gps.append(g)
        # cria WeekendInfo por GP encontrado (sem data precisa, usa ordem como round)
        for idx, gp in enumerate(uniq_gps[:24], start=1):
            weekends.append(
                WeekendInfo(
                    season="2026",
                    round=str(idx),
                    race_name=f"GP de {gp}",
                    circuit_name=gp,
                    locality="",
                    country="",
                    date="2026",
                    time=None,
                    sessions={"source": "ge.globo.com"},
                )
            )
        if weekends:
            return weekends
        # fallback: se nada, retorna 1 genérico baseado na home
        if home_html:
            # tenta pegar próxima corrida do título da home
            m = re.search(r'"title":"([^"]*GP[^"]*)"', home_html)
            race_name = m.group(1).strip() if m else "F1 — ge.globo"
            try:
                race_name = race_name.encode("utf-8").decode("unicode_escape")
            except Exception:
                pass
            return [
                WeekendInfo(
                    season="2026",
                    round="?",
                    race_name=race_name[:80],
                    circuit_name="ge.globo.com",
                    locality="",
                    country="Brasil",
                    date="2026",
                    time=None,
                    sessions={"source": "ge.globo.com"},
                )
            ]
        return []

    # ---------- WeekendProvider ----------

    async def get_current_schedule(self) -> list[WeekendInfo]:
        try:
            home = await self._fetch(self.home_url)
            cal = await self._fetch(self.calendario_url)
            weekends = self._parse_calendario(cal, home)
            if weekends:
                return weekends
        except Exception:
            pass
        # fallback último recurso
        try:
            home = await self._fetch(self.home_url)
            return self._parse_calendario(home, home)
        except Exception:
            return [
                WeekendInfo(
                    season="2026",
                    round="?",
                    race_name="F1 — ge.globo",
                    circuit_name="ge.globo.com",
                    locality="",
                    country="Brasil",
                    date="2026",
                    time=None,
                    sessions={},
                )
            ]

    async def get_next_weekend(self) -> WeekendInfo:
        sched = await self.get_current_schedule()
        if sched:
            # tenta achar "Itália", "Monza" etc como próximo, senão primeiro
            for w in sched:
                if "itália" in w.race_name.lower() or "italia" in w.race_name.lower() or "monza" in w.circuit_name.lower():
                    return w
            return sched[0]
        return WeekendInfo(season="2026", round="?", race_name="F1 — ge.globo", circuit_name="", locality="", country="Brasil", date="2026", time=None, sessions={})

    async def get_weekend(self, year: str, round: str) -> WeekendInfo:
        sched = await self.get_current_schedule()
        if round.isdigit():
            idx = int(round) - 1
            if 0 <= idx < len(sched):
                return sched[idx]
            for w in sched:
                if w.round == round:
                    return w
        # fallback: retorna next
        return await self.get_next_weekend()

    async def get_session_results(self, year: str, round: str, session: SessionType) -> list[SessionResultItem]:
        """
        ge.globo não tem resultados numéricos por sessão; retorna:
        - para treinos/sprint/qualificação/corrida -> notícias como contexto para LLM
        - para calendário, a LLM usará WeekendInfo + notícias
        """
        try:
            html = await self._fetch(self.home_url)
            noticias = self._parse_noticias(html)
            # para todas as sessões, retorna notícias (limita 10)
            # diferencia por sessão apenas no label, mas conteúdo é o mesmo pool
            return self._noticias_to_results(noticias)
        except Exception:
            return []


# alias para factory
GeProvider = GloboProvider
