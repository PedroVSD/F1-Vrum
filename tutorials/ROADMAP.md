# Roadmap — RaceHub F1 API

> Guia passo-a-passo para construir o projeto **na mão**. Cada fase tem objetivo, arquivos envolvidos e checklist de verificação. Faça na ordem — cada fase depende da anterior.

**Stack alvo:** `FastAPI + PostgreSQL + SQLAlchemy 2.0 + Alembic + Pydantic + Docker Compose + Uvicorn` — `app/main.py:1`, `pyproject.toml:1`

---

## Visão Geral / Estado Atual (01/09/2026)

| Área | Status | Evidência |
|------|--------|-----------|
| Models ORM | ✅ 70% — `app/models/*.py` criados, relações definidas | `app/models/diagrama.mmd:1` |
| Schemas Pydantic | ⚠️ Parcial — só `driver.py`, `team.py` etc. vazios/incompletos | `app/schemas/driver.py:1` |
| Routers | ⚠️ `app/main.py:23` com rotas hardcoded, `app/routers/drivers.py:1` vazio | |
| Database / Session | ❌ `app/database/session.py:1` e `base.py:1` vazios | |
| Alembic / Migrations | ❌ Não existe | |
| Docker Compose | ❌ Não existe | |
| Módulo Weekend | ✅ Funcional isolado | `app/routers/weekend.py:1`, `app/services/weekend_service.py:1` |
| Auth / Testes / ETL | ❌ Não iniciado | `README.md:13` |

> O módulo `weekend` (`app/core/config.py:6`, `app/repositories/weekend_provider.py:1`) está desacoplado e **não bloqueia** as fases abaixo. Pode ser mantido como está.

---

## Fase 0 — Saneamento do Projeto (1-2h)

**Objetivo:** deixar o repo consistente antes de adicionar código.

- [ ] 0.1 Corrigir `pyproject.toml:2` — `name = "biblioteca-api"` → `racehub-api` ou `api-f1`
- [ ] 0.2 Atualizar `description` e `requires-python` (hoje exige `>=3.14` — confirme sua versão com `python --version`)
- [ ] 0.3 Adicionar deps que faltam: `pydantic`, `alembic`, `psycopg[binary]` ou `asyncpg`, `python-multipart`
  ```bash
  uv add pydantic alembic "psycopg[binary]" python-multipart
  ```
- [ ] 0.4 Criar `.env` a partir de `.env.example:1`
  ```bash
  cp .env.example .env
  ```
- [ ] 0.5 Verificar que `uv run uvicorn app.main:app --reload` sobe em `http://127.0.0.1:8000/docs`

**Sai com:** projeto roda limpo, sem warnings de import.

---

## Fase 1 — Correção dos Models e Diagrama ER (2-3h)

**Arquivos:** `app/models/*.py`, `app/models/base.py:1`, `app/models/diagrama.mmd:1`

Problemas atuais para corrigir **na mão**:

- [ ] 1.1 `Driver` (`app/models/driver.py:8`) precisa de `team_id`? Hoje `DriverCreate` pede `team_id` mas o Model não tem FK. Decida: relação `Driver N:1 Team` (histórico por temporada?) ou via `RaceResult`. Recomendado: adicionar `team_id` nullable + `relationship` ou criar tabela associativa `driver_teams` com `season_id`.
- [ ] 1.2 `Circuit.length_km` deveria ser `nullable`? Alguns circuitos históricos não têm dado.
- [ ] 1.3 `Race.date` (`app/models/race.py:19`) → mudar para `datetime` (precisa hora + timezone) + campo `round`, `status`.
- [ ] 1.4 `RaceResult.position` e `points` — permitir `nullable` para DNF/DNS.
- [ ] 1.5 Adicionar `__repr__` e `UniqueConstraint` (ex: `Driver.number` único por temporada).
- [ ] 1.6 Criar `app/models/__init__.py` exportando todos os models (necessário pro Alembic):
  ```python
  from app.models.base import Base
  from app.models.driver import Driver
  from app.models.team import Team
  # ... etc
  __all__ = ["Base", "Driver", ...]
  ```
- [ ] 1.7 Imports circulares: `app/models/team.py:3` importa `RaceResult` direto — use `TYPE_CHECKING` ou string annotation (`"RaceResult"`).

**Verificação:** `uv run python -c "from app.models.base import Base; import app.models.driver, app.models.team; print(Base.metadata.tables.keys())"`

---

## Fase 2 — Database Layer (3-4h) — PRIORIDADE MÁXIMA

**Arquivos:** `app/database/session.py:1`, `app/database/base.py:1`, `app/core/config.py:6`

- [ ] 2.1 Criar `app/core/config.py` — adicionar `DatabaseSettings` (ou estender `WeekendSettings`):
  ```python
  database_url: str = "postgresql+psycopg://user:pass@localhost:5432/racehub"
  # ou async: "postgresql+asyncpg://..."
  ```
  Ler via `pydantic-settings` com `env_file=".env"`.
- [ ] 2.2 Implementar `app/database/session.py`:
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from app.core.config import get_settings
  engine = create_engine(get_settings().database_url, echo=True)
  SessionLocal = sessionmaker(bind=engine, autoflush=False)
  def get_db(): ...
  ```
  Para async: `create_async_engine` + `async_sessionmaker`.
- [ ] 2.3 Implementar `app/database/base.py` — re-exportar `Base` de `app/models/base.py:1` ou criar `get_db` dependency.
- [ ] 2.4 Testar conexão:
  ```bash
  uv run python -c "from app.database.session import engine; print(engine.connect())"
  ```

**Verificação:** dependency `get_db` injetável em routers via `Depends`.

---

## Fase 3 — Schemas Pydantic (2-3h)

**Arquivos:** `app/schemas/*.py`

Cada entidade precisa de 4 schemas:

- [ ] 3.1 `Base` (campos comuns), `Create`, `Update`, `Response` (com `model_config = ConfigDict(from_attributes=True)`)
- [ ] 3.2 Exemplo `app/schemas/driver.py:6` — hoje só tem `DriverCreate`. Criar:
  ```python
  class DriverResponse(DriverCreate):
      id: int
      model_config = ConfigDict(from_attributes=True)
  class DriverUpdate(BaseModel):  # todos Optional
  ```
- [ ] 3.3 Repetir para: `team.py:1`, `circuit.py:1`, `race.py:1`, `season.py:1`, `result.py:1`, `pitstop.py:1`
- [ ] 3.4 Validar com `uv run python -m py_compile app/schemas/*.py`

---

## Fase 4 — Alembic + Migrações (1-2h)

- [ ] 4.1 Inicializar:
  ```bash
  uv run alembic init alembic
  ```
- [ ] 4.2 Configurar `alembic.ini` → `sqlalchemy.url` lendo de `app.core.config`
- [ ] 4.3 Configurar `alembic/env.py`:
  ```python
  from app.models.base import Base
  import app.models.driver, app.models.team, app.models.circuit, app.models.race, app.models.season, app.models.race_result, app.models.pitstop
  target_metadata = Base.metadata
  ```
- [ ] 4.4 Gerar e aplicar:
  ```bash
  uv run alembic revision --autogenerate -m "initial"
  uv run alembic upgrade head
  uv run alembic downgrade -1 && uv run alembic upgrade head  # teste
  ```

---

## Fase 5 — Docker Compose (Postgres + API) (1h)

Novo arquivo `docker-compose.yml` na raiz:

- [ ] 5.1 Serviço `db` (postgres:16, volume `pgdata`, env `POSTGRES_DB/USER/PASSWORD`)
- [ ] 5.2 Serviço `api` (build `Dockerfile`, `depends_on: db`, env `DATABASE_URL`)
- [ ] 5.3 Criar `Dockerfile`:
  ```dockerfile
  FROM python:3.12-slim
  COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen
  COPY . .
  CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- [ ] 5.4 Testar:
  ```bash
  docker compose up --build
  curl http://localhost:8000/docs
  ```

---

## Fase 6 — Repository Pattern (2-3h)

**Pasta:** `app/repositories/` (hoje só tem `weekend_provider.py:1`)

- [ ] 6.1 Criar `app/repositories/base.py` — classe genérica `BaseRepository[T]`
  ```python
  class BaseRepository(Generic[T]):
      def __init__(self, db: Session): ...
      def get(self, id: int) -> T | None: ...
      def list(self, skip, limit): ...
      def create(self, obj_in): ...
      def update(self, db_obj, obj_in): ...
      def delete(self, id): ...
  ```
- [ ] 6.2 Criar um arquivo por entidade: `driver_repo.py`, `team_repo.py`, `circuit_repo.py`, etc., herdando de `BaseRepository`.
- [ ] 6.3 Não colocar regra de negócio aqui — só queries.

**Verificação:** repositories testáveis com `Session` mockada.

---

## Fase 7 — Service Layer (2h)

**Pasta:** `app/services/` (hoje só `weekend_service.py:1`, `llm_service.py:1`, `notify_service.py:1`)

- [ ] 7.1 Criar `driver_service.py`, `team_service.py`, etc. — validam regras (ex: número do piloto único, data de corrida não no passado para `create`).
- [ ] 7.2 Services recebem `repository` via DI, nunca `Session` direto.
- [ ] 7.3 Levantar `HTTPException(404)` quando não encontrado — manter routers magros.

---

## Fase 8 — Routers CRUD (4-6h) — CORE DA API

**Arquivos:** `app/routers/*.py`, `app/main.py:12`

- [ ] 8.1 Limpar `app/main.py:23` — remover rotas hardcoded (`/drivers`, `/teams`, `/circuits`) e mover para routers dedicados.
- [ ] 8.2 Implementar `app/routers/drivers.py:1`:
  ```python
  from fastapi import APIRouter, Depends
  router = APIRouter(prefix="/drivers", tags=["drivers"])
  @router.get("/", response_model=list[DriverResponse])
  def list_drivers(db: Session = Depends(get_db)): ...
  @router.get("/{driver_id}", response_model=DriverResponse)
  @router.post("/", response_model=DriverResponse, status_code=201)
  @router.put("/{driver_id}", response_model=DriverResponse)
  @router.delete("/{driver_id}", status_code=204)
  ```
- [ ] 8.3 Repetir para `teams.py:1`, `races.py:1`, `circuits.py:1`, `seasons.py` (criar), `results.py` (criar)
- [ ] 8.4 Registrar no `app/main.py:12`:
  ```python
  from app.routers import drivers, teams, circuits, races
  app.include_router(drivers.router)
  # ...
  ```
- [ ] 8.5 Adicionar `description`, `summary`, `response_description` em cada endpoint (boa prática `README.md:173`).

**Verificação:** `curl http://127.0.0.1:8000/drivers | jq` e Swagger `http://127.0.0.1:8000/docs` com 5 grupos de rotas + `weekend`.

---

## Fase 9 — Paginação, Filtros e Ordenação (2h)

**Previsto em `README.md:16`**

- [ ] 9.1 Paginação: `skip: int = 0, limit: int = Query(20, le=100)` + header `X-Total-Count`
- [ ] 9.2 Filtros: `Query` params por entidade (ex: `GET /drivers?nationality=BRA&team_id=1`)
- [ ] 9.3 Ordenação: `order_by: str = Query("id")` validado contra whitelist
- [ ] 9.4 Criar `app/schemas/pagination.py` com `PaginatedResponse[T]`
- [ ] 9.5 Opcional: instalar `fastapi-pagination` para padronizar

---

## Fase 10 — Autenticação e Autorização (4-6h)

**Previsto em `README.md:18`**

- [ ] 10.1 Criar `app/models/user.py` (id, email, hashed_password, role)
- [ ] 10.2 Criar `app/core/security.py` — `pwd_context` (passlib/bcrypt), `create_access_token`, `verify_password`
- [ ] 10.3 Router `app/routers/auth.py` — `POST /auth/register`, `POST /auth/login` (OAuth2PasswordRequestForm), `GET /auth/me`
- [ ] 10.4 Dependency `get_current_user` via `OAuth2PasswordBearer`
- [ ] 10.5 Roles: `enum Role {admin, user}` + dependency `require_role("admin")` para `POST/PUT/DELETE`
- [ ] 10.6 Adicionar `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` no `.env` e `app/core/config.py:6`

---

## Fase 11 — Testes (3-4h)

**Boa prática `README.md:176`**

- [ ] 11.1 Configurar `pytest`, `httpx`, `pytest-asyncio`:
  ```bash
  uv add --dev pytest httpx pytest-asyncio faker
  ```
- [ ] 11.2 Criar `app/tests/conftest.py` — fixtures `client` (TestClient), `db` (sqlite memory ou postgres test)
- [ ] 11.3 Testes por camada:
  - `tests/test_drivers.py` — CRUD + 404 + paginação
  - `tests/test_auth.py` — login, token, acesso negado
  - `tests/test_weekend.py` — mock `JolpicaProvider` + `OllamaClient`
- [ ] 11.4 Rodar:
  ```bash
  uv run pytest -v --cov=app
  ```

---

## Fase 12 — ETL e Coleta de Dados (4-6h)

**Previsto em `README.md:21` / `app/repositories/weekend_provider.py:1`**

- [ ] 12.1 Escolher fonte primária: **Jolpica** (já implementada) → fallback **OpenF1** ou **ESPN scraping** (BeautifulSoup/Playwright)
- [ ] 12.2 Criar `app/etl/` ou `app/jobs/` desacoplado da API:
  - `jolpica_client.py` — busca `seasons`, `races`, `results`
  - `normalize.py` — mapeia JSON externo → models internos
  - `load.py` — upsert no Postgres (evitar duplicatas)
- [ ] 12.3 Comando CLI: `uv run python -m app.etl.load --year 2024`
- [ ] 12.4 Agendamento: `APScheduler` in-app ou `cron`/`n8n` chamando `POST /weekend/notify` (`README.md:133`)

---

## Fase 13 — Funcionalidades Avançadas (semanas)

| Feature | Arquivos | Notas |
|---------|----------|-------|
| **Estatísticas** `README.md:17` | `app/routers/standings.py`, `app/services/stats_service.py` | Queries agregadas: pontos por piloto/equipe, voltas mais rápidas, pitstops médios |
| **Favoritos** `README.md:20` | `app/models/favorite.py` (user_id, driver_id/team_id) | Requer auth |
| **Redis Cache** `README.md:26` | `app/core/cache.py` | Cachear `GET /drivers`, `GET /weekend/next` com TTL |
| **Rate limiting** | `slowapi` ou `redis` | Proteger `POST /auth/login` |
| **Predição** `README.md:23` | `app/ml/predict.py` | Random Forest/XGBoost em `race_results` → `POST /predict/podium` |
| **Dashboard** `README.md:24` | `frontend/` separado (Streamlit ou React) | Consome `GET /standings`, `GET /weekend/schedule` |
| **Nginx** `README.md:27` | `nginx.conf` | Reverse proxy + TLS |

---

## Fase 14 — Qualidade e Produção (2h)

- [ ] 14.1 Lint/format: `uv add --dev ruff` → `uv run ruff check . && uv run ruff format .`
- [ ] 14.2 Type check: `uv run pyright` (`pyproject.toml:15`)
- [ ] 14.3 Logging estruturado + `app/core/middleware.py` (request ID, tempo)
- [ ] 14.4 Variáveis de ambiente para credenciais (`README.md:25`) — nunca commitar `.env` (já em `.gitignore:13`)
- [ ] 14.5 CI: `.github/workflows/ci.yml` — `uv sync → ruff → pyright → pytest → docker build`
- [ ] 14.6 Documentação: atualizar `README.md:1` com endpoints finais + `http://127.0.0.1:8000/openapi.json`

---

## Ordem de Execução Sugerida (caminho crítico)

```
0 Saneamento
  → 1 Models
    → 2 Database + 4 Alembic (juntos)
      → 3 Schemas
        → 5 Docker
          → 6 Repositories → 7 Services → 8 Routers  (MVP usable)
            → 9 Paginação
              → 10 Auth
                → 11 Testes
                  → 12 ETL
                    → 13 Avançadas
                      → 14 Produção
```

**MVP mínimo para entregar valor:** Fases 0→8. Com isso `GET /drivers`, `GET /teams`, etc. já funcionam com Postgres real e Swagger completo.

---

## Checklist Final (Definition of Done)

- [ ] `docker compose up` sobe `api` + `db` sem erro
- [ ] `alembic upgrade head` aplica todas as tabelas (`Base.metadata`)
- [ ] Todos os CRUDs retornam `200/201/204/404` corretos e estão em `http://127.0.0.1:8000/docs`
- [ ] `pytest` com ≥70% cobertura
- [ ] `weekend` continua funcionando (`GET /weekend/health` → `configured: false` sem credenciais, `true` com)
- [ ] `.env.example` documenta todas as vars (já faz em `WeekendSettings`)
- [ ] `ruff` + `pyright` sem erros

---

## Referências no Código

- Stack e comandos: `README.md:43`, `pyproject.toml:7`
- Diagrama ER: `app/models/diagrama.mmd:1`
- Módulo weekend (exemplo de arquitetura limpa): `app/core/config.py:6`, `app/schemas/weekend.py:1`, `app/repositories/weekend_provider.py:1`, `app/services/weekend_service.py:1`, `app/routers/weekend.py:1`
- Models base: `app/models/base.py:1`, `app/database/session.py:1`
- Boas práticas: `README.md:172`

> Dica: use o módulo `weekend` como template — ele já segue `routers/services/schemas/core/repositories` (`README.md:57`). Replique o padrão para `drivers`, `teams`, etc.
