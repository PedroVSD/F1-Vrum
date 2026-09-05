# Tutorial 13.3 — Redis Cache + Rate Limit

## Passo 1 — Deps e Docker

```bash
uv add redis fastapi-cache2 slowapi
```

**`docker-compose.yml`** — adicione serviço:
```yaml
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

```bash
docker compose up --build
docker exec -it api-f1-redis-1 redis-cli ping # PONG
```

## Passo 2 — Cache

**`app/core/cache.py`** — crie:
```python
import redis
from app.core.config import get_settings
import json, functools

r = redis.Redis(host="redis", port=6379, decode_responses=True) # localhost se fora do docker: host="localhost"

def cache(ttl=60):
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key=f"{fn.__name__}:{args}:{kwargs}"
            if (cached:=r.get(key)): return json.loads(cached)
            result=await fn(*args, **kwargs) if callable(fn) else fn(*args, **kwargs)
            r.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return deco
```

Uso no router (`app/routers/drivers.py:1`):
```python
from app.core.cache import r
import json
@router.get("/")
def list_drivers(skip=0, limit=20, db=Depends(get_db)):
    key=f"drivers:{skip}:{limit}"
    if cached:=r.get(key): return json.loads(cached)
    data=svc.list(skip,limit)
    r.setex(key, 30, json.dumps([d.__dict__ for d in data], default=str))
    return data
```

Para `GET /weekend/next` cache 300s, para standings 60s.

Invalidação: no `POST/PUT/DELETE` faça `r.delete("drivers:*")` ou `r.flushdb()` simples.

## Passo 3 — Rate Limit

**`app/main.py:1`**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter=Limiter(key_func=get_remote_address)
app.state.limiter=limiter
```

No auth:
```python
from slowapi import Limiter
limiter=Limiter(key_func=get_remote_address)
@router.post("/auth/login")
@limiter.limit("5/minute")
def login(...): ...
```

## Verificação
```bash
curl http://127.0.0.1:8000/drivers | jq # 1ª hit DB
curl http://127.0.0.1:8000/drivers | jq # 2ª hit Redis
docker exec -it api-f1-redis-1 redis-cli keys "*"
ab -n 10 -c 2 http://127.0.0.1:8000/drivers # teste carga
```
