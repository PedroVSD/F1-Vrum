from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.race_result import RaceResult

from .base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    principal: Mapped[str]
    engine: Mapped[str]
    car: Mapped[str]
    results: Mapped[list["RaceResult"]] = relationship(back_populates="team")
