from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    points: Mapped[int]
    boss: Mapped[str]
    engine: Mapped[str]
    car: Mapped[str]
    country: Mapped[str]

    drivers: Mapped[list["Driver"]] = relationship(back_populates="team")
