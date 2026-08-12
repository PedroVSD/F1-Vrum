from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.driver import Driver
from app.models.pitstop import PitStop
from app.models.race import Race
from app.models.team import Team

from .base import Base


class RaceResult(Base):
    __tablename__ = "race_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    position: Mapped[int]
    points: Mapped[float]
    race: Mapped["Race"] = relationship(back_populates="results")
    driver: Mapped["Driver"] = relationship(back_populates="results")
    team: Mapped["Team"] = relationship(back_populates="results")
    pitstops: Mapped[list["PitStop"]] = relationship(
        back_populates="result",
        cascade="all, delete-orphan",
    )
