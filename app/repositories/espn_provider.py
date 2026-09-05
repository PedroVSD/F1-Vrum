"""
Provider ESPN - scraping leve das duas páginas indicadas:

- Classificação: https://www.espn.com.br/f1/classificacao  -> tabela de pilotos (PTS)
- Notícias:      https://www.espn.com.br/f1/               -> headlines JSON embutido

Implementa WeekendProvider para ser plugável no WeekendService
sem alterar nenhum outro arquivo (ver app/services/weekend_service.py).

Fallbacks: se parsing falhar ou ESPN bloquear, retorna lista vazia ou
WeekendInfo genérico em vez de quebrar o pipeline.
"""

import re

import httpx

from app.schemas.weekend import SessionResultItem, SessionType, WeekendInfo

ESPN_CLASSIFICACAO_URL = "https://www.espn.com.br/f1/classificacao"
ESPN_F1_URL = "https://www.espn.com.br/f1/"
ESPN_TIMEOUT = 15.0
HEADERS = {"User-Agent": "Mozilla/5.0 (RaceHub F1 API)"}


class EspnProvider:
    """Scraping ESPN BR. Usa regex + BeautifulSoup quando disponível."""

    def __init__(
        self,
        classificacao_url: str = ESPN_CLASSIFICACAO_URL,
        f1_url: str = ESPN_F1_URL,
    ):
        self.classificacao_url = classificacao_url
        self.f1_url = f1_url

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=ESPN_TIMEOUT, follow_redirects=True, headers=HEADERS
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    # ---------- helpers parsing ----------

    def _parse_classificacao(self, html: str) -> list[SessionResultItem]:
        """Extrai pilotos e PTS da tabela de classificação."""
        # Tentativa 1: regex rápida (funciona sem bs4)
        # padrão visto: <span class="hide-mobile">Nome</span> ... <span class="stat-cell">PTS</span>
        pattern = re.compile(
            r'<span class="hide-mobile">(.*?)</span>.*?<span class="stat-cell">(.*?)</span>',
            re.DOTALL,
        )
        matches = pattern.findall(html)
        results: list[SessionResultItem] = []
        for idx, (driver, pts) in enumerate(matches, start=1):
            driver = driver.strip()
            pts = pts.strip()
            if not driver:
                continue
            results.append(
                SessionResultItem(
                    position=str(idx),
                    driver=driver,
                    team="",  # ESPN não expõe equipe na tabela simplificada
                    points=pts,
                    time=None,
                    status=None,
                )
            )
        if results:
            return results

        # Tentativa 2: BeautifulSoup fallback
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            drivers = soup.select("span.hide-mobile")
            pts_cells = soup.select("span.stat-cell")
            for idx, (d, p) in enumerate(zip(drivers, pts_cells), start=1):
                driver = d.get_text(strip=True)
                pts = p.get_text(strip=True)
                if driver:
                    results.append(
                        SessionResultItem(
                            position=str(idx),
                            driver=driver,
                            team="",
                            points=pts,
                        )
                    )
            return results
        except Exception:
            pass
        return []

    def _parse_noticias(self, html: str) -> list[dict]:
        """Extrai headlines e links de notícias da home F1."""
        # JSON embutido: "headline":"Título"
        headlines = re.findall(r'"headline"\s*:\s*"([^"]+)"', html)
        # links /f1/noticia/_/id/...
        links = re.findall(r'href="(/f1/noticia/_/id/\d+[^"]*)"', html)
        # dedup mantendo ordem
        seen = set()
        uniq_titles = []
        for h in headlines:
            # decodifica unicode escape se vier \u00e3o
            try:
                h = h.encode("utf-8").decode("unicode_escape")
            except Exception:
                pass
            h = h.strip()
            if h and h not in seen and len(h) > 15 and "Customize" not in h:
                seen.add(h)
                uniq_titles.append(h)
        # pega até 10
        noticias = []
        for i, title in enumerate(uniq_titles[:10]):
            link = links[i] if i < len(links) else ""
            if link and not link.startswith("http"):
                link = "https://www.espn.com.br" + link
            noticias.append({"title": title, "link": link})
        return noticias

    def _noticias_to_results(self, noticias: list[dict]) -> list[SessionResultItem]:
        """Converte notícias em SessionResultItem para exibir no Telegram/LLM."""
        out = []
        for idx, n in enumerate(noticias, start=1):
            out.append(
                SessionResultItem(
                    position=str(idx),
                    driver=n["title"][:60],  # usa título como 'driver' para reaproveitar schema
                    team="ESPN Notícia",
                    time=n["link"] or None,
                    points=None,
                    status=None,
                )
            )
        return out

    def _parse_corrida_quali(self, html: str) -> list[SessionResultItem]:
        """Extrai grid de largada (qualificação) da página /f1/corrida/_/id/"""
        # padrão: RacingPos__Position + RacingPos__Name + RacingPos__Manufacturer (+ time em outra tabela)
        pos_pattern = re.compile(
            r'RacingPos__Position[^>]*>(\d+)</div>.*?RacingPos__Name[^>]*>([^<]+)</div>.*?RacingPos__Manufacturer[^>]*>([^<]+)</div>',
            re.DOTALL,
        )
        matches = pos_pattern.findall(html)
        results = []
        # tenta pegar tempo da quali na tabela de sessões: Qualificação -> 1:21.786
        sess_time = None
        m_time = re.search(r'Qualifi[^<]*</td>.*?RacingSessions__Time[^>]*>([^<]+)</td>', html, re.DOTALL)
        if m_time:
            sess_time = m_time.group(1).strip()
        for pos, driver, team in matches[:10]:
            results.append(
                SessionResultItem(
                    position=pos.strip(),
                    driver=driver.strip(),
                    team=team.strip(),
                    time=sess_time if pos.strip() == "1" else None,  # só pole tem tempo nessa página
                    points=None,
                    status=None,
                )
            )
        return results

    async def _get_latest_corrida_html(self) -> str | None:
        """Busca id da última corrida no calendário e retorna html da corrida."""
        try:
            cal_html = await self._fetch("https://www.espn.com.br/f1/calendario")
            # pega primeiro id de corrida: /f1/corrida/_/id/6000...
            m = re.search(r'/f1/corrida/_/id/(\d+)', cal_html)
            if m:
                corrida_id = m.group(1)
                return await self._fetch(f"https://www.espn.com.br/f1/corrida/_/id/{corrida_id}")
        except Exception:
            pass
        # fallback id conhecido de Monza 2025 (funciona como exemplo)
        try:
            return await self._fetch("https://www.espn.com.br/f1/corrida/_/id/600057442")
        except Exception:
            return None

    # ---------- WeekendProvider impl ----------

    async def get_current_schedule(self) -> list[WeekendInfo]:
        """ESPN não tem calendário estruturado; retorna lista com próxima corrida estimada."""
        try:
            w = await self.get_next_weekend()
            return [w]
        except Exception:
            return []

    async def get_next_weekend(self) -> WeekendInfo:
        """Tenta inferir próxima corrida a partir das notícias; fallback genérico."""
        try:
            html = await self._fetch(self.f1_url)
            # headlines contêm "GP da Itália", "GP da Holanda"
            headlines = re.findall(r'"headline"\s*:\s*"([^"]+)"', html)
            # procura GP
            next_gp = None
            for h in headlines:
                if "GP" in h or "Grande Prêmio" in h:
                    next_gp = h
                    try:
                        next_gp = next_gp.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        pass
                    break
            race_name = next_gp.strip() if next_gp else "Próxima Corrida F1 (ESPN)"
            # tenta extrair país
            # fallback fixo: usa classificação como contexto
            return WeekendInfo(
                season="2026",
                round="?",
                race_name=race_name[:80],
                circuit_name="Circuito (ver ESPN)",
                locality="Brasil",
                country="Brasil",
                date="2026",
                time=None,
                sessions={},
            )
        except Exception:
            return WeekendInfo(
                season="2026",
                round="?",
                race_name="F1 - ESPN",
                circuit_name="ESPN F1",
                locality="",
                country="Brasil",
                date="2026",
                time=None,
                sessions={},
            )

    async def get_weekend(self, year: str, round: str) -> WeekendInfo:
        # ESPN não tem histórico por ano/round, delega para next
        return await self.get_next_weekend()

    async def get_session_results(
        self, year: str, round: str, session: SessionType
    ) -> list[SessionResultItem]:
        """
        Mapeamento ESPN:
        - race / sprint -> classificação (PTS) de https://www.espn.com.br/f1/classificacao
        - qualifying / sprint_qualifying -> grid de largada (top 10) da página da corrida
        - fp1/fp2/fp3 -> notícias como placeholder
        """
        if session in (SessionType.race, SessionType.sprint):
            try:
                html = await self._fetch(self.classificacao_url)
                results = self._parse_classificacao(html)
                if results:
                    return results
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return []
                raise
            except Exception:
                return []
            return []
        if session in (SessionType.qualifying, SessionType.sprint_qualifying):
            try:
                html = await self._get_latest_corrida_html()
                if html:
                    results = self._parse_corrida_quali(html)
                    if results:
                        return results
                # fallback para classificação se parsing da corrida falhar
                html = await self._fetch(self.classificacao_url)
                return self._parse_classificacao(html)[:10]
            except Exception:
                return []
        else:
            # Treinos -> notícias como placeholder de "resultados"
            try:
                html = await self._fetch(self.f1_url)
                noticias = self._parse_noticias(html)
                return self._noticias_to_results(noticias)
            except Exception:
                return []


# Alias para compatibilidade com factory
EspnStandingsProvider = EspnProvider
EspnNewsProvider = EspnProvider
