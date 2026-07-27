from pydantic import BaseModel


class DriverCreate(BaseModel):
    first_name: str
    last_name: str
    number: int
    nationality: str
    team_id: int
