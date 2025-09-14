from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from mcp_bioforensics.db.models import DatasetRegistry

__all__ = [
    "DatasetInfo",
    "upsert_dataset",
    "get_dataset",
    "list_datasets",
    "save_mapping",
    "load_mapping",
]


@dataclass(slots=True)
class DatasetInfo:
    dataset_id: str
    name: str
    source_path: str | None
    row_count: int
    ingested_at: date | None
    notes: str | None

    @classmethod
    def from_row(cls, row: DatasetRegistry) -> DatasetInfo:
        return cls(
            dataset_id=row.dataset_id,
            name=row.name,
            source_path=row.source_path,
            row_count=row.row_count or 0,
            ingested_at=row.ingested_at,
            notes=row.notes,
        )


# ---------------------------- CRUD helpers ----------------------------


def upsert_dataset(
    session: Session,
    *,
    dataset_id: str,
    name: str,
    source_path: str | None = None,
    mapping: dict[str, Any] | None = None,
    row_count: int | None = None,
    notes: str | None = None,
    ingested_at: date | None = None,
) -> DatasetInfo:
    """Create or update a dataset registry record and return a summary."""
    row = session.get(DatasetRegistry, dataset_id)
    if row is None:
        row = DatasetRegistry(dataset_id=dataset_id, name=name)

    row.name = name
    row.source_path = source_path
    row.mapping_json = mapping
    if row_count is not None:
        row.row_count = int(row_count)
    row.notes = notes
    row.ingested_at = ingested_at or date.today()

    session.merge(row)
    session.commit()
    return DatasetInfo.from_row(row)


def get_dataset(session: Session, dataset_id: str) -> DatasetInfo | None:
    row = session.get(DatasetRegistry, dataset_id)
    return DatasetInfo.from_row(row) if row else None


def list_datasets(session: Session) -> list[DatasetInfo]:
    rows = session.query(DatasetRegistry).order_by(DatasetRegistry.dataset_id).all()
    return [DatasetInfo.from_row(r) for r in rows]


# ---------------------------- mapping helpers ----------------------------


def save_mapping(session: Session, dataset_id: str, mapping: dict[str, Any]) -> None:
    row = session.get(DatasetRegistry, dataset_id)
    if row is None:
        # Create a placeholder if not present
        row = DatasetRegistry(dataset_id=dataset_id, name=dataset_id)
    row.mapping_json = mapping
    session.merge(row)
    session.commit()


def load_mapping(session: Session, dataset_id: str) -> dict[str, Any] | None:
    row = session.get(DatasetRegistry, dataset_id)
    return row.mapping_json if row else None
