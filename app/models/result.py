from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Result(Base):
    __tablename__ = "result"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    race_id: Mapped[int]
    drive_id: Mapped[int]
    position: Mapped[int]
    points: Mapped[int]
