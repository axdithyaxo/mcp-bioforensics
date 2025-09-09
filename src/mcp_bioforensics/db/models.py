from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Date

class Base(DeclarativeBase):
    pass

class Trial(Base):
    __tablename__ = "trials"
    trial_id: Mapped[str] = mapped_column(String, primary_key=True)
    disease: Mapped[str] = mapped_column(String, index=True)
    phase: Mapped[str] = mapped_column(String, index=True)
    n_participants: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(String)
    outcomes_text: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    sponsor: Mapped[str] = mapped_column(String)
    start_date: Mapped[Date] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date] = mapped_column(Date, nullable=True)
