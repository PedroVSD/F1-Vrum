# RaceHub 
### É uma plataforma de dados, com uma API servindo os dados desenvolvida em FastAPI para disponibilizar informações sobre a Fórmula 1.

De início a plataforma permitirá consultar:

- Pilotos
- Equipes
- Circuitos
- Corridas
- Temporadas
- Resultados

No futuro a plataforma terá:

- Paginação
- Estatísticas
- Login
- Favoritos
- Coleta de dados separado
- ETL
- Predições
- Dashboard
- Variáveis de ambiente para credenciais.
- Redis
- Nginx

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

- uv venv
- source .venv/bin/activate
- uv run uvicorn app.main:app --reload
- http://127.0.0.1:8000
- Caso o comando acima falhar: uv run python -m uvicorn app.main:app --reload

- Para conectar em um provedor de API como insomina:
http://127.0.0.1:8000/openapi.json

- Para acessar o swagger
http://127.0.0.1:8000/docs

# Arquitetura planejada(pode mudar)

## Endpoints
#### Escrever descrições claras nos endpoints desde o início.
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
- Separar responsabilidades
- Testes
