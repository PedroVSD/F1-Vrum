from pydantic import BaseModel


class CircuitCreate(BaseModel):
    id: int
    name: str
    country: str
    city: str
    length_km: float
