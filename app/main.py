from fastapi import FastAPI


app = FastAPI()

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
