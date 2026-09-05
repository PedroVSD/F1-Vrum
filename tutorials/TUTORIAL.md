# Tutorial — RaceHub F1 API (faça na mão)

> Copie e cole. Ordem importa. Tudo dentro de `/home/pedrovsd/Códigos/APIs/api-f1`. Weeknd já está pronto (`app/routers/weekend.py:6`) — não mexa nele.

## 0. Pré-requisitos

```bash
python --version # precisa >=3.12 (pyproject pede >=3.14, mas 3.12 funciona)
uv --version
# dentro do projeto
uv sync
cp .env.example .env # já tem WEEKEND_PROVIDER, OLLAMA_*, TELEGRAM_*
```

---

## Fase 0 — Saneamento (15 min)

**1. `pyproject.toml:2`**
```toml
name = "racehub-api"
description = "API F1 - pilotos, equipes, circuitos, corridas"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.139.2",
  "sqlalchemy>=2.0.51",
  "uvicorn>=0.51.0",
  "httpx>=0.28.1",
  "pydantic-settings>=2.8.1",
  "pydantic>=2.0.0",
  "beautifulsoup4>=4.15.0",
  "lxml>=6.1.3",
  "psycopg[binary]>=3.2.0", # ou asyncpg
  "alembic>=1.13.0",
  "python-multipart>=0.0.9",
]
```

```bash
uv add pydantic "psycopg[binary]" alembic python-multipart
uv run python -c "from app.main import app; print('ok')"
```

---

## Fase 1 — Fix Models (30 min)

**Arquivos:** `app/models/*.py`, `app/models/base.py:1`, `app/models/diagrama.mmd:1`

**1.1 `app/models/base.py:1`** (já ok, só garanta)
```python
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
```

**1.2 `app/models/__init__.py`** — crie:
```python
from app.models.base import Base
from app.models.driver import Driver
from app.models.team import Team
from app.models.circuit import Circuit
from app.models.season import Season
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.pitstop import PitStop
__all__ = ["Base","Driver","Team","Circuit","Season","Race","RaceResult","PitStop"]
```

**1.3 `app/models/driver.py:8`** — adicione FK opcional:
```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
class Driver(Base):
    __tablename__="drivers"
    id: Mapped[int]=mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    number: Mapped[int]
    nationality: Mapped[str]
    birth_date: Mapped[date]
    team_id: Mapped[int | None]=mapped_column(ForeignKey("teams.id"), nullable=True)
    team: Mapped["Team | None"]=relationship(back_populates="drivers")
```

**1.4 `app/models/team.py:1`** — evite import circular:
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
class Team(Base):
    __tablename__="teams"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    principal: Mapped[str]
    engine: Mapped[str]
    car: Mapped[str]
    drivers: Mapped[list["Driver"]]=relationship(back_populates="team")
    results: Mapped[list["RaceResult"]]=relationship(back_populates="team")
```

**1.5 `app/models/race.py:19`** — mude para datetime+round:
```python
from datetime import datetime
class Race(Base):
    __tablename__="races"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]
    season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id"))
    circuit_id: Mapped[int]=mapped_column(ForeignKey("circuits.id"))
    round: Mapped[int]
    date: Mapped[datetime] # antes era date
    season: Mapped["Season"]=relationship(back_populates="races")
    results: Mapped[list["RaceResult"]]=relationship(back_populates="race")
```

**1.6 `app/models/circuit.py:1`** — nullable:
```python
length_km: Mapped[float | None]
```

**1.7 `app/models/race_result.py:1`** — nullable para DNF:
```python
position: Mapped[int | None]
points: Mapped[float | None]
status: Mapped[str | None]
```

Verifique:
```bash
uv run python -c "from app.models.base import Base; import app.models.driver,app.models.team,app.models.circuit,app.models.race,app.models.season,app.models.race_result,app.models.pitstop; print(list(Base.metadata.tables.keys()))"
```

---

## Fase 2 — Database Layer (40 min)

**2.1 `app/core/config.py:6`** — adicione DB url (já tem WeekendSettings):
```python
database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/racehub"
# para testes use: sqlite:///./test.db
```

**2.2 `app/database/session.py:1`** — crie:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
```

**2.3 `app/database/base.py:1`** — só re-exporte:
```python
from app.models.base import Base
__all__ = ["Base"]
```

Teste:
```bash
# sem postgres ainda, use sqlite temporário:
# mude .env DATABASE_URL=sqlite:///./racehub.db
uv run python -c "from app.database.session import engine; conn=engine.connect(); print('conectou', conn); conn.close()"
```

---

## Fase 3 — Schemas Pydantic (40 min)

Para cada entidade crie 4 classes. Exemplo `app/schemas/driver.py:6` — substitua:

```python
from datetime import date
from pydantic import BaseModel, ConfigDict

class DriverBase(BaseModel):
    first_name: str; last_name: str; number: int; nationality: str; birth_date: date; team_id: int | None = None

class DriverCreate(DriverBase): pass
class DriverUpdate(BaseModel):
    first_name: str | None=None; last_name: str | None=None; number: int | None=None; nationality: str | None=None; birth_date: date | None=None; team_id: int | None=None
class DriverResponse(DriverBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

Repita para `team.py`, `circuit.py`, `race.py`, `season.py`, `result.py`, `pitstop.py` — mesmo padrão (id + from_attributes).

Valide:
```bash
uv run python -m py_compile app/schemas/*.py
```

---

## Fase 4 — Alembic (20 min)

```bash
uv run alembic init alembic
```

**`alembic.ini`** — troque `sqlalchemy.url`:
```ini
sqlalchemy.url = postgresql+psycopg://postgres:postgres@localhost:5432/racehub
```

**`alembic/env.py`** — edite imports:
```python
from app.models.base import Base
import app.models.driver, app.models.team, app.models.circuit, app.models.race, app.models.season, app.models.race_result, app.models.pitstop
target_metadata = Base.metadata
# leia url do config:
from app.core.config import get_settings
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

```bash
uv run alembic revision --autogenerate -m "initial"
uv run alembic upgrade head
# teste downgrade/upgrade
uv run alembic downgrade -1 && uv run alembic upgrade head
```

---

## Fase 5 — Docker Compose (20 min)

**`Dockerfile`** na raiz:
```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache
COPY . .
CMD ["uv","run","python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

**`docker-compose.yml`**:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: racehub
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [db]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/racehub
volumes: {pgdata: {}}
```

```bash
docker compose up --build
# em outro terminal
curl http://localhost:8000/weekend/health | jq
curl http://localhost:8000/docs
```

---

## Fase 6 — Repositories (30 min)

**`app/repositories/base.py`** — crie:
```python
from typing import Generic, TypeVar, Type
from sqlalchemy.orm import Session
T=TypeVar("T")
class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]): self.db=db; self.model=model
    def get(self, id:int): return self.db.get(self.model, id)
    def list(self, skip=0, limit=20): return self.db.query(self.model).offset(skip).limit(limit).all()
    def create(self, obj_in: dict): obj=self.model(**obj_in); self.db.add(obj); self.db.commit(); self.db.refresh(obj); return obj
    def update(self, db_obj, obj_in: dict):
        for k,v in obj_in.items():
            if v is not None: setattr(db_obj,k,v)
        self.db.commit(); self.db.refresh(db_obj); return db_obj
    def delete(self, id:int):
        obj=self.get(id)
        if obj: self.db.delete(obj); self.db.commit()
        return obj
```

**`app/repositories/driver_repo.py`**:
```python
from app.repositories.base import BaseRepository
from app.models.driver import Driver
from sqlalchemy.orm import Session
class DriverRepository(BaseRepository[Driver]):
    def __init__(self, db: Session): super().__init__(db, Driver)
```

Repita para `team_repo.py`, `circuit_repo.py`, `race_repo.py`, `season_repo.py`.

---

## Fase 7 — Services (30 min)

**`app/services/driver_service.py`**:
```python
from fastapi import HTTPException
from app.repositories.driver_repo import DriverRepository
class DriverService:
    def __init__(self, repo: DriverRepository): self.repo=repo
    def get(self, id:int):
        obj=self.repo.get(id)
        if not obj: raise HTTPException(404, "Driver not found")
        return obj
    def list(self, skip=0, limit=20): return self.repo.list(skip,limit)
    def create(self, data: dict): # valide number único
        return self.repo.create(data)
    def update(self, id:int, data:dict): return self.repo.update(self.get(id), data)
    def delete(self, id:int): 
        if not self.repo.delete(id): raise HTTPException(404, "Driver not found")
```

Repita para demais entidades.

---

## Fase 8 — Routers CRUD (60 min) — MVP

**1. Limpe `app/main.py:23`** — remova 3 rotas hardcoded, deixe só:
```python
from fastapi import FastAPI
from app.routers.weekend import router as weekend_router
from app.routers import drivers, teams, circuits, races, seasons

app=FastAPI(title="RaceHub - F1 API", version="0.2.0")
app.include_router(weekend_router)
app.include_router(drivers.router)
app.include_router(teams.router)
app.include_router(circuits.router)
app.include_router(races.router)
app.include_router(seasons.router)

@app.get("/")
def home(): return "Bem vindo ao F1 vrum"
```

**2. `app/routers/drivers.py:1`** — substitua vazio por:
```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.driver_repo import DriverRepository
from app.services.driver_service import DriverService
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse

router=APIRouter(prefix="/drivers", tags=["drivers"])
def get_service(db: Session=Depends(get_db)): return DriverService(DriverRepository(db))

@router.get("/", response_model=list[DriverResponse], summary="Lista pilotos")
def list_drivers(skip:int=0, limit:int=20, svc=Depends(get_service)): return svc.list(skip,limit)
@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id:int, svc=Depends(get_service)): return svc.get(driver_id)
@router.post("/", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
def create_driver(payload: DriverCreate, svc=Depends(get_service)): return svc.create(payload.model_dump())
@router.put("/{driver_id}", response_model=DriverResponse)
def update_driver(driver_id:int, payload: DriverUpdate, svc=Depends(get_service)): return svc.update(driver_id, payload.model_dump(exclude_unset=True))
@router.delete("/{driver_id}", status_code=204)
def delete_driver(driver_id:int, svc=Depends(get_service)): svc.delete(driver_id); return
```

Copie o arquivo para `teams.py`, `circuits.py`, `races.py`, `seasons.py` trocando nomes.

Verifique:
```bash
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
curl http://127.0.0.1:8000/docs | head
curl http://127.0.0.1:8000/drivers | jq
curl -X POST http://127.0.0.1:8000/drivers -H "Content-Type: application/json" -d '{"first_name":"Gabriel","last_name":"Bortoleto","number":5,"nationality":"BRA","birth_date":"2004-10-14"}' | jq
```

---

## Fase 9 — Paginação/Filtros (20 min)

No router, troque `list` para:
```python
from fastapi import Query
@router.get("/")
def list_drivers(skip:int=Query(0, ge=0), limit:int=Query(20, le=100), nationality: str | None=None, svc=Depends(get_service)):
    q=svc.repo.db.query(svc.repo.model)
    if nationality: q=q.filter(svc.repo.model.nationality==nationality)
    return q.offset(skip).limit(limit).all()
```
Crie `app/schemas/pagination.py` opcional. Ou instale `uv add fastapi-pagination`.

---

## Fase 10 — Auth (60 min) — depois do MVP

```bash
uv add passlib[bcrypt] python-jose[cryptography]
```

**`app/models/user.py`**:
```python
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(unique=True)
    hashed_password: Mapped[str]
    role: Mapped[str]=mapped_column(default="user") # admin/user
```

**`app/core/security.py`**: `pwd_context`, `create_access_token`, `verify_password`, `get_current_user` via `OAuth2PasswordBearer`.

**`app/routers/auth.py`**: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`. Adicione `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` em `app/core/config.py:6`.

Proteja `POST/PUT/DELETE` com `Depends(require_role("admin"))`.

---

## Fase 11 — Testes (30 min)

```bash
uv add --dev pytest httpx pytest-asyncio faker
mkdir -p tests
```

**`tests/conftest.py`**: fixtures `client` (TestClient) + `db` sqlite memory.

```bash
uv run pytest -v
```

---

## Fase 12 — ETL (40 min)

Crie `app/etl/jolpica_client.py` (já tem lógica em `app/repositories/weekend_provider.py:40` + `espn_provider.py:1` + `openf1_provider.py:28`), `app/etl/normalize.py`, `app/etl/load.py` com upsert.

```bash
uv run python -m app.etl.load --year 2024
# agende: cron ou n8n chamando POST /weekend/notify
```

---

## Fase 13-14 — Avançado

* **Estatísticas:** `app/routers/standings.py` → queries agregadas pontos.
* **Favoritos:** `app/models/favorite.py` (user_id, driver_id).
* **Redis:** `uv add redis` + `app/core/cache.py` para cachear `GET /drivers`.
* **Nginx:** `nginx.conf` reverse proxy.
* **ML:** `app/ml/predict.py` com `scikit-learn`/`xgboost`.
* **Qualidade:** `uv add --dev ruff` → `uv run ruff check . && uv run ruff format .` + `uv run pyright`

---

## Checklist Final

```bash
docker compose up --build
uv run alembic upgrade head
curl http://127.0.0.1:8000/drivers | jq # 200
curl http://127.0.0.1:8000/weekend/health | jq # weekend True
uv run pytest
uv run ruff check . && uv run pyright
```

MVP = Fases 0-8. Após isso você já tem `GET/POST/PUT/DELETE` real com Postgres + Swagger completo.
