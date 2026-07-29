from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Race(Base):
    __tablename__ = "race"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    season_id = Column(Integer)
    circuit_id = Column(Integer)
    date = Column(Integer)
