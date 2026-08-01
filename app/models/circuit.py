from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Circuit(Base):
    __tablename__ = "circuit"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str]
    country: Mapped[str]
    city: Mapped[str]
    length_km: Mapped[float]
