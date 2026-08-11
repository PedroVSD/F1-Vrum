from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Interval

from .base import Base


class PitStop(Base):
    __tablename__ = "pitstops"

    id: Mapped[int] = mapped_column(primary_key=True)
    duration: Mapped[Interval]

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    team: Mapped["Team"] = relationship(back_populates="pitstops")
