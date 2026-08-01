from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Race(Base):
    __tablename__ = "race"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    season_id: Mapped[int]
    circuit_id: Mapped[int]
    date: Mapped[int]
