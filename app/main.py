from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return "Bem vindo ao F1 vrum"

@app.get("/ola")
def ola():
    return {"Message": "Olá da API"}

@app.get("/carros-f1")
def carros():
    lista_carros = ["RBR, Ferrari, Mclaren, Mercedes"]
    return lista_carros
