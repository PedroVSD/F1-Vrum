from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    principal: Mapped[str]
    engine: Mapped[str]
    car: Mapped[str]

    drivers: Mapped[list["Driver"]] = relationship(back_populates="team")
