from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "team"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    drivers = Column(String)
    points = Column(Integer)
    boss = Column(String)
    engine = Column(String)
    car = Column(String)
    country = Column(String)
