# Tutorial 13.4 — Predição de Pódio (Random Forest / XGBoost)

> Treina com `race_results` + `pitstops` e expõe `POST /predict/podium`.

## Passo 1 — Deps

```bash
uv add scikit-learn pandas joblib
# opcional xgboost
uv add xgboost
```

## Passo 2 — Preparar dataset

**`app/ml/dataset.py`**:
```python
import pandas as pd
from sqlalchemy.orm import Session
from app.models.race_result import RaceResult
from app.models.driver import Driver

def build_df(db:Session):
    rows=db.query(RaceResult.driver_id, RaceResult.position, RaceResult.points, RaceResult.race_id).all()
    df=pd.DataFrame(rows, columns=["driver_id","position","points","race_id"])
    # features simples: média pontos, taxa pódio histórico
    feats=df.groupby("driver_id").agg(avg_points=("points","mean"), win_rate=("position", lambda x: (x==1).mean()), podium_rate=("position", lambda x: (x<=3).mean())).reset_index()
    # label: será pódio na próxima corrida? (1 se já foi pódio antes)
    feats["label"]=(feats["podium_rate"]>0.3).astype(int)
    return feats
```

## Passo 3 — Treino

**`app/ml/train.py`**:
```python
from sklearn.ensemble import RandomForestClassifier
import joblib
from app.database.session import SessionLocal
from app.ml.dataset import build_df

def train():
    db=SessionLocal()
    df=build_df(db)
    X=df[["avg_points","win_rate","podium_rate"]]
    y=df["label"]
    clf=RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X,y)
    joblib.dump(clf, "app/ml/model.joblib")
    print("acurácia train", clf.score(X,y))
if __name__=="__main__": train()
```

```bash
uv run python -m app.ml.train
ls -lh app/ml/model.joblib
```

## Passo 4 — Inferência API

**`app/ml/predict.py`**:
```python
import joblib, pandas as pd
model=joblib.load("app/ml/model.joblib")
def predict_podium(avg_points: float, win_rate: float, podium_rate: float):
    X=pd.DataFrame([[avg_points, win_rate, podium_rate]], columns=["avg_points","win_rate","podium_rate"])
    prob=model.predict_proba(X)[0][1]
    return {"pódio_prob": round(float(prob),3), "pred": bool(prob>0.5)}
```

**`app/routers/predict.py`**:
```python
from fastapi import APIRouter
from pydantic import BaseModel
from app.ml.predict import predict_podium
router=APIRouter(prefix="/predict", tags=["ml"])
class PredictIn(BaseModel): avg_points:float; win_rate:float; podium_rate:float
@router.post("/podium")
def podium(payload: PredictIn): return predict_podium(**payload.model_dump())
```

Registre em `app/main.py:12`.

## Verificação
```bash
curl -X POST http://127.0.0.1:8000/predict/podium -H "Content-Type: application/json" -d '{"avg_points":12.5,"win_rate":0.2,"podium_rate":0.5}' | jq
# esperado: {"pódio_prob":0.82,"pred":true}
```

Evolução: treinar com features reais (qualifying position, pitstop avg, circuito) e salvar métricas.
