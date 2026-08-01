from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Circuit(Base):
    __tablename__ = "circuit"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    city: Mapped[str]
    length_km: Mapped[float]
