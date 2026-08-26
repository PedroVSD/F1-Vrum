# RaceHub 
### É uma plataforma de dados, com uma API servindo os dados desenvolvida em FastAPI para disponibilizar informações sobre a Fórmula 1🏎️.

De início a plataforma permitirá consultar:

- Pilotos
- Equipes
- Circuitos
- Corridas
- Temporadas
- Resultados

No futuro a plataforma terá:

- Automação para informar horários, pódios etc. Provavelmente usando n8n ou algo do tipo
- Paginação, filtros e ordenação
- Estatísticas
- Login, roles
- Autenticação (JWT, OAuth2, Password hash, etc)
- Favoritos
- Coleta de dados separado
- ETL
- Predições(Random Forest ou XGBoost pra prever pódio ou pontuação)
- Dashboard
- Variáveis de ambiente para credenciais.
- Redis
- Nginx
- Streamlit ou um dashboard em react para visualizar estatísticas

## Atualizando dados sobre as corridas:
Como ideia de atualização dos dados, como corridas, temporadas e etc. Puxar os dados de um site atualizado (ESPN por exemplo)-> fazendo um web scraping, ou puxar de alguma API que contenha os dados.

# Stack

- FastAPI
- PostgreSQL
- SQLAlchemy2.0
- Alembic
- Pydantic
- Docker Compose
- Uvicorn

# Rodando o projeto

```bash
uv venv
source .venv/bin/activate
uv sync
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000
# Caso o comando acima falhar:
uv run python -m uvicorn app.main:app --reload
```

## Módulo: Atualizações de fim de semana de corrida (NOVO)

Fluxo isolado que respeita a estrutura existente do projeto (`routers/services/schemas/core/repositories`):

```
Sites de esporte (Jolpica F1 API) -> API interna -> Ollama Cloud (LLM edita msg) -> Email/Telegram
```

Cobre: **Treinos (FP1/FP2/FP3), Sprint, Qualificação e Corrida.**

### Arquitetura (seguindo padrão FastAPI do projeto)

```
app/core/config.py              -> WeekendSettings (lê .env via pydantic-settings)
app/schemas/weekend.py          -> SessionType, WeekendInfo, NotifyRequest/Response
app/repositories/weekend_provider.py -> JolpicaProvider (adapter para trocar por ESPN/OpenF1)
app/services/llm_service.py     -> OllamaClient (https://ollama.com/api/chat) com fallback
app/services/notify_service.py  -> EmailNotifier (SMTP) + TelegramNotifier (Bot API)
app/services/weekend_service.py -> orquestra ingest -> llm -> notify
app/routers/weekend.py          -> endpoints FastAPI (/weekend/*)
```

**Fallbacks:** sem `OLLAMA_API_KEY` envia mensagem bruta; sem SMTP/Telegram apenas reporta `configured: false`; sem resultados ainda, envia grade de horários.

### Configuração (.env)

Copie `.env.example` para `.env`:

```bash
cp .env.example .env
# edite com suas chaves
```

Variáveis principais (ver `.env.example`):

| Var | Descrição |
|-----|-----------|
| `OLLAMA_API_KEY` | Key do https://ollama.com/settings/keys |
| `OLLAMA_MODEL` | default `llama3.1:8b` |
| `SMTP_HOST/PORT/USER/PASSWORD/TO` | SMTP para email |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Bot do @BotFather + chat |

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/weekend/health` | Confere se LLM/email/telegram estão configurados |
| GET | `/weekend/next` | Próxima corrida (circuito, data, horários) |
| GET | `/weekend/schedule` | Calendário completo da temporada |
| GET | `/weekend/preview?session_type=qualifying` | Mensagem bruta sem LLM/sem envio |
| POST | `/weekend/notify` | Pipeline completo (ingest -> LLM -> envio) |

Exemplos:

```bash
# saúde
curl http://127.0.0.1:8000/weekend/health

# próxima corrida
curl http://127.0.0.1:8000/weekend/next

# prévia sem envio
curl "http://127.0.0.1:8000/weekend/preview?session_type=race&year=2024&round=1"

# pipeline completo (dry_run para testar sem enviar)
curl -X POST http://127.0.0.1:8000/weekend/notify \
  -H "Content-Type: application/json" \
  -d '{"session_type":"qualifying","dry_run":true}'

# envio real para canais configurados
curl -X POST http://127.0.0.1:8000/weekend/notify \
  -H "Content-Type: application/json" \
  -d '{"session_type":"race","channels":["telegram"]}'

# via swagger: http://127.0.0.1:8000/docs
```

### Agendamento (cron/n8n/APScheduler)

O módulo é stateless. Para receber todo fim de semana automaticamente, agende chamadas a `POST /weekend/notify`:

- **n8n/cron**: `0 18 * * 5,6,0 curl -X POST .../weekend/notify -d '{"session_type":"qualifying"}'` etc.
- **APScheduler** (in-app): adicionar job que chama `process_weekend()` nos horários de cada sessão.

### Trocar fonte de dados

Implemente `WeekendProvider` em `app/repositories/weekend_provider.py` (ex: `EspnScraper`, `OpenF1Provider`) e injete em `app/services/weekend_service.py`. Nenhum outro arquivo precisa mudar.

- Para conectar em um provedor de API como insomina:
http://127.0.0.1:8000/openapi.json

- Para acessar o swagger
http://127.0.0.1:8000/docs

# Arquitetura planejada(pode mudar)

## Endpoints

- GET /drivers
- GET /drivers{id}
- POST /driver
- PUT /drivers{id}
- GET /teams
- GET /races
- GET /circuits
- GET /standings
- DELETE /driver{id}

## Arquitetura
- routers/
- services/
- repositories/
- models/
- schemas/
- database/
- core/

# Como boas práticas:
- Ir documentando
- Escrever descrições claras nos endpoints desde o início
- Separar responsabilidades
- Testes
