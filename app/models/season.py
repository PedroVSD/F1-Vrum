from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.race import Race

from .base import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
    races: Mapped[list["Race"]] = relationship(back_populates="season")
