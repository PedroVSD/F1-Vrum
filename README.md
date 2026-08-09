# RaceHub é uma API REST desenvolvida em FastAPI para disponibilizar informações sobre a Fórmula 1.

## Atualizando dados sobre as corridas:
Puxas os dados de um site atualizado (ESPN por exemplo)-> aqui fazer um web scraping, ou puxar de alguma API que contenha os dados

A API permitirá consultar:

- Pilotos
- Equipes
- Circuitos
- Corridas
- Temporadas
- Resultados

No futuro haverá:

- Login
- Favoritos
- Predições
- Estatísticas
- Dashboard

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
