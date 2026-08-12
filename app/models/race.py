from datetime import date

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from app.models.race_result import RaceResult
from app.models.season import Season

from .base import Base


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuits.id"))
    date: Mapped[date]
    season: Mapped["Season"] = relationship(back_populates="races")
    results: Mapped[list["RaceResult"]] = relationship(back_populates="race")
