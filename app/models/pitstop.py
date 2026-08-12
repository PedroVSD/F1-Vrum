from datetime import timedelta

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Interval

from app.models.race_result import RaceResult

from .base import Base


class PitStop(Base):
    __tablename__ = "pitstops"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("race_results.id"))
    stop_number: Mapped[int]
    duration: Mapped[timedelta] = mapped_column(Interval)
    result: Mapped["RaceResult"] = relationship(back_populates="pitstops")
