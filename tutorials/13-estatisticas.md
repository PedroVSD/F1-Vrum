# Tutorial 13.1 — Estatísticas (Standings)

> Agregações sobre `race_results` + `pitstops`. Depende de Fases 0-8 (DB + CRUD).

## Objetivo
`GET /standings/drivers?season=2025` e `GET /standings/teams` retornando pontos, vitórias, pódios, voltas mais rápidas.

## Passo 1 — Service

**`app/services/stats_service.py`** — crie:
```python
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.models.race_result import RaceResult
from app.models.driver import Driver
from app.models.team import Team
from app.models.race import Race

class StatsService:
    def __init__(self, db: Session): self.db=db

    def driver_standings(self, season_id: int | None=None):
        q=self.db.query(
            Driver.id, Driver.first_name, Driver.last_name, Driver.number,
            func.sum(RaceResult.points).label("total_points"),
            func.count(case((RaceResult.position==1, 1))).label("wins"),
            func.count(case((RaceResult.position.in_([1,2,3]), 1))).label("podiums"),
        ).join(RaceResult, RaceResult.driver_id==Driver.id)
        if season_id:
            q=q.join(Race, Race.id==RaceResult.race_id).filter(Race.season_id==season_id)
        q=q.group_by(Driver.id).order_by(func.sum(RaceResult.points).desc())
        return q.all()

    def team_standings(self, season_id: int | None=None):
        q=self.db.query(
            Team.id, Team.name,
            func.sum(RaceResult.points).label("total_points"),
        ).join(RaceResult, RaceResult.team_id==Team.id)
        if season_id:
            q=q.join(Race, Race.id==RaceResult.race_id).filter(Race.season_id==season_id)
        return q.group_by(Team.id).order_by(func.sum(RaceResult.points).desc()).all()

    def avg_pitstop(self, driver_id:int):
        from app.models.pitstop import PitStop
        return self.db.query(func.avg(PitStop.duration)).join(RaceResult, PitStop.result_id==RaceResult.id).filter(RaceResult.driver_id==driver_id).scalar()
```

## Passo 2 — Schemas

**`app/schemas/standings.py`**:
```python
from pydantic import BaseModel
class DriverStanding(BaseModel):
    driver_id:int; first_name:str; last_name:str; number:int
    total_points:float; wins:int; podiums:int
class TeamStanding(BaseModel):
    team_id:int; name:str; total_points:float
```

## Passo 3 — Router

**`app/routers/standings.py`**:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.stats_service import StatsService
router=APIRouter(prefix="/standings", tags=["standings"])
@router.get("/drivers")
def drivers(season_id:int|None=None, db:Session=Depends(get_db)):
    return StatsService(db).driver_standings(season_id)
@router.get("/teams")
def teams(season_id:int|None=None, db:Session=Depends(get_db)):
    return StatsService(db).team_standings(season_id)
@router.get("/pitstop/{driver_id}")
def pitstop_avg(driver_id:int, db:Session=Depends(get_db)):
    return {"driver_id":driver_id, "avg_seconds": StatsService(db).avg_pitstop(driver_id)}
```

**`app/main.py:12`** adicione:
```python
from app.routers import standings
app.include_router(standings.router)
```

## Verificação
```bash
uv run python -c "from app.services.stats_service import StatsService; print('ok')"
curl "http://127.0.0.1:8000/standings/drivers?season_id=1" | jq
curl "http://127.0.0.1:8000/standings/teams" | jq
```
