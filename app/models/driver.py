from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primare_key=True)
    first_name = Column(String)
    last_name = Column(String)
    number = Column(Interger)
    nationality = Column(String)
    team_id = Column(Integer, ForeignKey=("teams.id"))
