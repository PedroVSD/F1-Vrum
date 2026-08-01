from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
