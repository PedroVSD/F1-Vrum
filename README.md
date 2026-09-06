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
- BeautifulSoup4 + lxml (scraping ESPN / ge.globo)
- httpx

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

## Módulo: Atualizações de fim de semana de corrida

Fluxo isolado que respeita a estrutura existente do projeto (`routers/services/schemas/core/repositories`):

```
Jolpica (Ergast) + ESPN Brasil + ge.globo + OpenF1 -> síntese multi-fonte (provider=all) -> API interna -> Ollama Cloud (LLM edita/sintetiza msg) -> Email/Telegram
```

Cobre: **Treinos (FP1/FP2/FP3), Sprint, Qualificação e Corrida.** Suporta `provider=jolpica|espn|globo|openf1|all` ou lista `jolpica,espn,globo`.

### Arquitetura (seguindo padrão FastAPI do projeto)

```
app/core/config.py              -> WeekendSettings (lê .env via pydantic-settings)
app/schemas/weekend.py          -> SessionType, WeekendInfo, NotifyRequest/Response (provider=jolpica|espn|globo|openf1|all)
app/repositories/weekend_provider.py -> JolpicaProvider (Ergast)
app/repositories/espn_provider.py    -> EspnProvider (https://www.espn.com.br/f1/classificacao + https://www.espn.com.br/f1/)
app/repositories/globo_provider.py   -> GloboProvider (https://ge.globo.com/motor/formula-1/)
app/repositories/openf1_provider.py  -> OpenF1Provider (https://api.openf1.org/v1)
app/services/llm_service.py     -> OllamaClient (https://ollama.com/api/chat) com fallback
app/services/notify_service.py  -> EmailNotifier (SMTP) + TelegramNotifier (Bot API)
app/services/weekend_service.py -> orquestra ingest (get_providers/build_multi_source_raw) -> llm -> notify (suporta síntese multi-fonte)
app/routers/weekend.py          -> endpoints FastAPI (/weekend/* ?provider=all)
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
| `WEEKEND_PROVIDER` | `jolpica` (default) \| `espn` \| `globo` \| `openf1` \| `all` (síntese 4 fontes) ou lista `jolpica,espn,globo` |
| `JOLPICA_BASE_URL` | default `https://api.jolpi.ca/ergast/f1` |
| `ESPN_CLASSIFICACAO_URL` / `ESPN_F1_URL` | `https://www.espn.com.br/f1/classificacao` e `https://www.espn.com.br/f1/` |
| `GLOBO_HOME_URL` / `GLOBO_CALENDARIO_URL` | `https://ge.globo.com/motor/formula-1/` e artigo de calendário |
| `OPENF1_BASE_URL` | default `https://api.openf1.org/v1` |
| `OLLAMA_API_KEY` | Key do https://ollama.com/settings/keys |
| `OLLAMA_MODEL` | default `llama3.1:8b` |
| `SMTP_HOST/PORT/USER/PASSWORD/TO` | SMTP para email |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Bot do @BotFather + chat |

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/weekend/health` | Confere se LLM/email/telegram e providers estão configurados |
| GET | `/weekend/next?provider=globo` | Próxima corrida (aceita `jolpica`\|`espn`\|`globo`\|`openf1`\|`all`) |
| GET | `/weekend/schedule?provider=all` | Calendário completo (sintetiza 4 fontes se `all`) |
| GET | `/weekend/preview?session_type=qualifying&provider=espn` | Mensagem bruta sem LLM/sem envio (use `fp1` para notícias) |
| POST | `/weekend/notify` | Pipeline completo (ingest -> LLM síntese -> envio), aceita `provider` |

Exemplos:

```bash
# saúde (mostra providers)
curl http://127.0.0.1:8000/weekend/health | jq

# próxima corrida — por provider
curl "http://127.0.0.1:8000/weekend/next?provider=jolpica" | jq
curl "http://127.0.0.1:8000/weekend/next?provider=globo" | jq
curl "http://127.0.0.1:8000/weekend/next?provider=all" | jq

# prévia sem envio — notícias vs classificação
curl "http://127.0.0.1:8000/weekend/preview?session_type=fp1&provider=espn" | jq # notícias ESPN
curl "http://127.0.0.1:8000/weekend/preview?session_type=fp1&provider=globo" | jq # notícias ge.globo
curl "http://127.0.0.1:8000/weekend/preview?session_type=qualifying&provider=espn" | jq # grid top10
curl "http://127.0.0.1:8000/weekend/preview?session_type=race&provider=all" | jq # síntese 4 fontes

# pipeline completo (dry_run para testar sem enviar)
curl -X POST http://127.0.0.1:8000/weekend/notify \
  -H "Content-Type: application/json" \
  -d '{"session_type":"qualifying","provider":"all","dry_run":true}' | jq

# envio real — single provider
curl -X POST http://127.0.0.1:8000/weekend/notify \
  -H "Content-Type: application/json" \
  -d '{"session_type":"race","provider":"globo","channels":["telegram"]}' | jq

# envio real — síntese multi-fonte (recomendado)
curl -X POST http://127.0.0.1:8000/weekend/notify \
  -H "Content-Type: application/json" \
  -d '{"session_type":"fp1","provider":"all","channels":["telegram"]}' | jq

# via swagger: http://127.0.0.1:8000/docs
```

### Agendamento (cron/n8n/APScheduler)

O módulo é stateless. Para receber todo fim de semana automaticamente, agende chamadas a `POST /weekend/notify`:

- **n8n/cron**: `0 18 * * 5,6,0 curl -X POST .../weekend/notify -d '{"session_type":"qualifying"}'` etc.
- **APScheduler** (in-app): adicionar job que chama `process_weekend()` nos horários de cada sessão.

### Trocar fonte de dados

Implemente `WeekendProvider` (ex: `EspnProvider`, `GloboProvider`, `OpenF1Provider`) em `app/repositories/` e registre em `app/services/weekend_service.py:14` (`get_provider`/`get_providers`). Use `?provider=globo` ou `provider=all` para síntese multi-fonte (Jolpica+ESPN+globo+OpenF1 → LLM sintetiza). Nenhum outro arquivo precisa mudar.

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
