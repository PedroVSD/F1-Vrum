# Tutorial Avançado — Partes 13-14 (Índice)

> Continuação de `TUTORIAL.md:1` (Fases 0-12 já cobrem MVP). Rode Fases 0-8 antes.

| Arquivo | O que entrega | Tempo |
|---------|---------------|-------|
| `tutorials/13-estatisticas.md` | `GET /standings/drivers|teams`, `avg pitstop` com agregações SQLAlchemy | 30 min |
| `tutorials/13-favoritos.md` | `app/models/favorite.py:1`, CRUD por `user_id` (requer Auth Fase 10) | 30 min |
| `tutorials/13-redis.md` | `docker-compose redis:7`, cache `GET /drivers` + `slowapi` rate limit | 20 min |
| `tutorials/13-predicao.md` | `app/ml/train.py`, `RandomForest`/`XGBoost` + `POST /predict/podium` | 45 min |
| `tutorials/13-dashboard.md` | `dashboard/app.py` Streamlit ou `frontend/` React consumindo `openapi.json` | 30 min |
| `tutorials/13-nginx.md` | `nginx.conf` + `docker-compose nginx:alpine` como reverse proxy | 15 min |
| `tutorials/14-qualidade.md` | `ruff`, `pyright`, `middleware RequestId`, `.github/workflows/ci.yml` | 20 min |

## Ordem recomendada

```
13-estatisticas → 13-favoritos → 13-redis → 13-predicao → 13-dashboard → 13-nginx → 14-qualidade
```

Cada arquivo é independente e tem comandos `uv`, código pronto e `curl` de verificação. Todos ficam em `tutorials/` dentro do projeto.
