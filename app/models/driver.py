from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    number: Mapped[int]
    nationality: Mapped[str]
    birth_date: Mapped[date]
