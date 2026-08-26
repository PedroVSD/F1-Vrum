from fastapi import FastAPI

from app.routers.weekend import router as weekend_router

app = FastAPI(
    title="RaceHub - F1 API",
    description="API de Fórmula 1 com módulo de atualizações de fim de semana (treinos/sprint/quali/corrida) via Ollama Cloud + email/telegram",
    version="0.2.0",
)

# Módulo isolado: fim de semana de corrida (não altera rotas existentes)
app.include_router(weekend_router)


@app.get("/")
def home():
    return "Bem vindo ao F1 vrum"

@app.get("/ola")
def ola():
    return {"Message": "Olá da API"}

@app.get("/drivers")
def drivers():
    lista_drivers = ["Verstappen, Leclerc, Antonelli"]
    return lista_drivers

@app.get("/teams")
def teams():
    teams_list = ["RBR, Ferrari, Mclaren, Mercedes"]
    return teams_list

@app.get("/circuits")
def circuits():
    return ["Monza", "Interlagos", "Silverstone"]
