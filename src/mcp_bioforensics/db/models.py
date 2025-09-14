from typing import Any

from sqlalchemy import JSON, Date, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):  # type: ignore[misc]
    """SQLAlchemy 2.0 Declarative base.

    mypy may not recognize `DeclarativeBase` without sqlalchemy-stubs; we suppress the
    misc error here to keep strict mode enabled elsewhere.
    """

    pass


class Trial(Base):
    """Canonical clinical trial row.

    We use a composite primary key (dataset_id, trial_id) so the same trial_id
    in different datasets does not collide. All rows carry dataset_id.
    Arbitrary extra columns from source CSVs can be stored in `extras` (JSON).
    """

    __tablename__ = "trials"

    # Composite PK for multi-dataset support
    dataset_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    trial_id: Mapped[str] = mapped_column(String, primary_key=True)

    disease: Mapped[str] = mapped_column(String, index=True)
    phase: Mapped[str] = mapped_column(String, index=True)
    n_participants: Mapped[int] = mapped_column(Integer)

    summary: Mapped[str] = mapped_column(String)
    outcomes_text: Mapped[str] = mapped_column(String)

    status: Mapped[str] = mapped_column(String)
    sponsor: Mapped[str] = mapped_column(String)

    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # Free-form, lossless capture of source-specific columns
    extras: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class DatasetRegistry(Base):
    """Registry of datasets that have been ingested.

    Stores provenance and the per-dataset column mapping used during ingestion.
    """

    __tablename__ = "dataset_registry"

    dataset_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)

    # Optional provenance
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    # Persisted mapping and stats
    mapping_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    ingested_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
