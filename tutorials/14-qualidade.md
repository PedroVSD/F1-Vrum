# Tutorial 14 — Qualidade e Produção

## 14.1 Lint/Format (Ruff)

```bash
uv add --dev ruff
uv run ruff check . --fix
uv run ruff format .
```

Adicione em `pyproject.toml`:
```toml
[tool.ruff]
line-length=100
[tool.ruff.lint]
select=["E","F","I","UP"]
```

## 14.2 Type Check (Pyright)

`pyproject.toml` já tem:
```toml
[tool.pyright]
venvPath="."
venv=".venv"
typeCheckingMode="standard"
```

```bash
uv run pyright
# corrija: adicione `from __future__ import annotations` e `TYPE_CHECKING` onde há import circular (team.py:3)
```

## 14.3 Logging Estruturado + Middleware

**`app/core/middleware.py`** — crie:
```python
import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid=str(uuid.uuid4())[:8]
        start=time.time()
        response=await call_next(request)
        response.headers["X-Request-Id"]=rid
        response.headers["X-Process-Time"]=str(round(time.time()-start,3))
        print(f"[{rid}] {request.method} {request.url.path} -> {response.status_code} {round(time.time()-start,3)}s")
        return response
```

**`app/main.py:1`**:
```python
from app.core.middleware import RequestIdMiddleware
app.add_middleware(RequestIdMiddleware)
```

## 14.4 Variáveis de Ambiente

Já em `.gitignore:13` (`.env` ignorado). Garanta `.env.example` completo (`app/core/config.py:6` lê via `pydantic-settings`):
```bash
cat .env.example # deve ter WEEKEND_PROVIDER, DATABASE_URL, SECRET_KEY, OLLAMA_*, TELEGRAM_*, SMTP_*
# nunca commite .env
git check-ignore .env # deve retornar .env
```

Adicione em `app/core/config.py:6`:
```python
secret_key: str = "change-me"
algorithm: str = "HS256"
access_token_expire_minutes: int = 30
```

## 14.5 CI (GitHub Actions)

**`.github/workflows/ci.yml`** — crie:
```yaml
name: ci
on: [push, pull_request]
jobs:
  ci:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: racehub}
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pyright
      - run: uv run pytest -q
      - run: docker compose up --build -d && sleep 5 && curl -f http://localhost:8000/weekend/health
```

## 14.6 Documentação

Atualize `README.md:1` com endpoints finais:
```md
## Endpoints finais
GET /drivers, POST /drivers, GET /teams, GET /circuits, GET /races, GET /standings/drivers, POST /predict/podium, GET /weekend/next
Swagger: http://127.0.0.1:8000/docs
OpenAPI: http://127.0.0.1:8000/openapi.json
```

## Verificação Final

```bash
uv run ruff check . && echo "ruff ok"
uv run pyright && echo "pyright ok"
uv run pytest -q && echo "tests ok"
docker compose up --build -d && curl -s http://localhost:80/weekend/health | jq
```
