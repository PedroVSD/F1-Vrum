from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Season(Base):
    __tablename__ = "season"

    id = Column(Integer, primary_key=True)
    year = Column(Integer)
