from sqlalchemy import Double, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Circuit(Base):
    __tablename__ = "circuit"

    id = Column(Integer, primare_key=True)
    name = Column(String)
    country = Column(String)
    city = Column(String)
    length_km = Column(Double)
