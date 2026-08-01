from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
