from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    drivers: Mapped[str]
    points: Mapped[int]
    boss: Mapped[str]
    engine: Mapped[str]
    car: Mapped[str]
    country: Mapped[str]
