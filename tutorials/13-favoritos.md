# Tutorial 13.2 — Favoritos (requer Auth Fase 10)

## Objetivo
`POST /favorites/drivers/{driver_id}`, `GET /favorites`, `DELETE /favorites/{id}` por usuário logado.

## Passo 1 — Model

**`app/models/favorite.py`** — crie:
```python
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
class Favorite(Base):
    __tablename__="favorites"
    __table_args__=(UniqueConstraint("user_id","driver_id", name="uq_fav_driver"), UniqueConstraint("user_id","team_id", name="uq_fav_team"))
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    driver_id: Mapped[int|None]=mapped_column(ForeignKey("drivers.id"), nullable=True)
    team_id: Mapped[int|None]=mapped_column(ForeignKey("teams.id"), nullable=True)
    user: Mapped["User"]=relationship()
```

Adicione em `app/models/__init__.py` o import.

```bash
uv run alembic revision --autogenerate -m "add favorites"
uv run alembic upgrade head
```

## Passo 2 — Schema

**`app/schemas/favorite.py`**:
```python
from pydantic import BaseModel, ConfigDict
class FavoriteCreate(BaseModel): driver_id:int|None=None; team_id:int|None=None
class FavoriteResponse(BaseModel):
    id:int; user_id:int; driver_id:int|None; team_id:int|None
    model_config=ConfigDict(from_attributes=True)
```

## Passo 3 — Service + Router

**`app/services/favorite_service.py`**:
```python
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.favorite import Favorite
class FavoriteService:
    def __init__(self, db:Session): self.db=db
    def list(self, user_id:int): return self.db.query(Favorite).filter_by(user_id=user_id).all()
    def add(self, user_id:int, driver_id=None, team_id=None):
        if not driver_id and not team_id: raise HTTPException(400,"Informe driver_id ou team_id")
        fav=Favorite(user_id=user_id, driver_id=driver_id, team_id=team_id)
        self.db.add(fav); self.db.commit(); self.db.refresh(fav); return fav
    def remove(self, fav_id:int, user_id:int):
        fav=self.db.get(Favorite, fav_id)
        if not fav or fav.user_id!=user_id: raise HTTPException(404,"Favorite not found")
        self.db.delete(fav); self.db.commit()
```

**`app/routers/favorites.py`**:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import get_current_user
from app.services.favorite_service import FavoriteService
from app.schemas.favorite import FavoriteCreate
router=APIRouter(prefix="/favorites", tags=["favorites"])
@router.get("/")
def list_favs(db:Session=Depends(get_db), user=Depends(get_current_user)):
    return FavoriteService(db).list(user.id)
@router.post("/", status_code=201)
def add(payload:FavoriteCreate, db:Session=Depends(get_db), user=Depends(get_current_user)):
    return FavoriteService(db).add(user.id, payload.driver_id, payload.team_id)
@router.delete("/{fav_id}", status_code=204)
def remove(fav_id:int, db:Session=Depends(get_db), user=Depends(get_current_user)):
    FavoriteService(db).remove(fav_id, user.id); return
```

Registre em `app/main.py:12` e proteja com `get_current_user` (Fase 10).

## Verificação
```bash
# login primeiro
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login -d "username=teste@a.com&password=123" | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/favorites | jq
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://127.0.0.1:8000/favorites -d '{"driver_id":1}' | jq
```
