from datetime import date

from pydantic import BaseModel


class DriverCreate(BaseModel):
    first_name: str
    last_name: str
    number: int
    nationality: str
    birth_date: date
    team_id: int
