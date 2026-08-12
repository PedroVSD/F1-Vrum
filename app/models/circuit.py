from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Circuit(Base):
    __tablename__ = "circuits"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    city: Mapped[str]
    length_km: Mapped[float]
