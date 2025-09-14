from datetime import date, datetime
from typing import Any

import pandas as pd

from mcp_bioforensics.db.models import Base, DatasetRegistry, Trial
from mcp_bioforensics.db.session import SessionLocal, engine


def _coerce_str(x: Any) -> str:
    """Safe string coercion that converts NaN/None to empty string and strips whitespace."""
    if x is None:
        return ""
    try:
        s = str(x)
    except Exception:
        return ""
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s.strip()


def _coerce_int(x: Any, default: int = 0) -> int:
    """Robust integer coercion from strings/floats; returns default on failure."""
    if x is None:
        return default
    try:
        if isinstance(x, bool):  # guard against True/False becoming 1/0 unexpectedly
            return int(x)
        if isinstance(x, int):
            return int(x)
        if isinstance(x, float):
            if pd.isna(x):
                return default
            return int(x)
        # strings or other types
        s = str(x).strip().replace(",", "")
        if s.lower() in {"nan", "", "none", "null"}:
            return default
        return int(float(s))
    except Exception:
        return default


def _parse_date(x: Any) -> date | None:
    """Parse common date formats to `date`; returns None on failure.

    Accepts strings like YYYY-MM-DD, DD-MM-YYYY, MM/DD/YYYY, and long month formats.
    """
    if x is None:
        return None
    s = _coerce_str(x)
    if not s:
        return None
    # Try common formats
    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%b %d, %Y",  # Jan 02, 2020
        "%B %d, %Y",  # January 02, 2020
    )
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_phase(phase: Any) -> str:
    """Canonicalize trial phases to PHASE* tokens expected by the DB."""
    s = _coerce_str(phase).lower()
    if not s:
        return ""
    mapping = {
        "1": "PHASE1",
        "phase 1": "PHASE1",
        "i": "PHASE1",
        "phase i": "PHASE1",
        "2": "PHASE2",
        "phase 2": "PHASE2",
        "ii": "PHASE2",
        "phase ii": "PHASE2",
        "3": "PHASE3",
        "phase 3": "PHASE3",
        "iii": "PHASE3",
        "phase iii": "PHASE3",
        "4": "PHASE4",
        "phase 4": "PHASE4",
        "iv": "PHASE4",
        "phase iv": "PHASE4",
        "1/2": "PHASE1|PHASE2",
        "phase 1/2": "PHASE1|PHASE2",
        "i/ii": "PHASE1|PHASE2",
        "2/3": "PHASE2|PHASE3",
        "phase 2/3": "PHASE2|PHASE3",
        "ii/iii": "PHASE2|PHASE3",
        "early phase 1": "EARLY_PHASE1",
        "not applicable": "NOT_APPLICABLE",
        "n/a": "NOT_APPLICABLE",
        "na": "NOT_APPLICABLE",
        "observational": "NOT_APPLICABLE",
    }
    return mapping.get(s, s.upper())


def _normalize_status(status: Any) -> str:
    s = _coerce_str(status)
    return s.capitalize() if s else ""


def _auto_map_columns(df: pd.DataFrame) -> dict[str, str]:
    """Guess canonical field mapping from a DataFrame (case-insensitive)."""
    canonical_fields = [
        "trial_id",
        "disease",
        "phase",
        "n_participants",
        "summary",
        "outcomes_text",
        "status",
        "sponsor",
        "start_date",
        "end_date",
    ]
    aliases = {
        "trial_id": [
            "nct_id",
            "nct number",
            "nct",
            "trial_id",
            "trialid",
            "trial id",
            "id",
            "study_id",
            "study id",
        ],
        "disease": ["condition", "conditions", "disease", "indication"],
        "phase": [
            "phase",
            "phases",
            "trial_phase",
            "study_phase",
            "phase(s)",
            "study phase",
            "trial phase",
        ],
        "n_participants": [
            "enrollment",
            "enrollment count",
            "participants",
            "n_participants",
            "num_participants",
            "number_participants",
            "sample_size",
        ],
        "summary": ["brief_summary", "brief summary", "summary", "description", "overview"],
        "outcomes_text": [
            "primary outcome measures",
            "secondary outcome measures",
            "outcomes",
            "other outcome measures",
            "outcomes_text",
            "results",
        ],
        "status": ["overall_status", "recruitment_status", "status", "trial_status"],
        "sponsor": ["sponsor", "lead sponsor", "sponsors", "funder", "funding_source"],
        "start_date": [
            "start_date",
            "study start",
            "study start date",
            "start",
            "begin_date",
            "date_started",
        ],
        "end_date": [
            "completion_date",
            "primary completion date",
            "end_date",
            "end",
            "date_completed",
        ],
    }
    df_cols_lower = {col.lower(): col for col in df.columns}
    mapping: dict[str, str] = {}
    for canon in canonical_fields:
        for alias in aliases.get(canon, [canon]):
            if alias.lower() in df_cols_lower:
                mapping[canon] = df_cols_lower[alias.lower()]
                break
    return mapping


def ingest_csv(
    path: str,
    dataset_id: str,
    dataset_name: str | None = None,
    mapping: dict[str, str] | None = None,
    notes: str | None = None,
) -> int:
    """Ingest a CSV into the DB under a dataset ID. Returns number of upserted rows.

    If `mapping` is omitted, columns are auto-mapped. Values are normalized for
    phase, status, participants, and dates. Unmapped columns are stored in `extras`.
    """
    df = pd.read_csv(path)

    # Auto-map if not provided
    if mapping is None:
        mapping = _auto_map_columns(df)

    # Ensure canonical columns exist; fill from mapped sources when present
    canon_cols = [
        "trial_id",
        "disease",
        "phase",
        "n_participants",
        "summary",
        "outcomes_text",
        "status",
        "sponsor",
        "start_date",
        "end_date",
    ]
    for c in canon_cols:
        if c not in df.columns:
            df[c] = None
        src = mapping.get(c)
        if src and src in df.columns:
            df[c] = df[src]

    # Normalize fields
    df["trial_id"] = df["trial_id"].map(_coerce_str)
    df["disease"] = df["disease"].map(_coerce_str)
    df["phase"] = df["phase"].map(_normalize_phase)
    df["status"] = df["status"].map(_normalize_status)
    df["summary"] = df["summary"].map(_coerce_str)
    df["outcomes_text"] = df["outcomes_text"].map(_coerce_str)
    df["sponsor"] = df["sponsor"].map(_coerce_str)
    df["n_participants"] = df["n_participants"].map(_coerce_int)

    # Dates
    df["start_date"] = df["start_date"].map(_parse_date)
    df["end_date"] = df["end_date"].map(_parse_date)

    # Drop rows missing ID
    df = df[df["trial_id"] != ""].copy()

    # Create tables if needed
    Base.metadata.create_all(engine)

    inserted = 0
    with SessionLocal() as session:
        # Upsert trials
        for _, row in df.iterrows():
            # Build extras excluding canonical keys; drop NaNs/None
            extras: dict[str, Any] = {}
            for col in df.columns:
                if col in {
                    "trial_id",
                    "disease",
                    "phase",
                    "n_participants",
                    "summary",
                    "outcomes_text",
                    "status",
                    "sponsor",
                    "start_date",
                    "end_date",
                }:
                    continue
                val = row.get(col)
                # Skip empties / NaNs
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    continue
                extras[col] = val

            trial = Trial(
                dataset_id=dataset_id,
                trial_id=_coerce_str(row.get("trial_id")),
                disease=_coerce_str(row.get("disease")),
                phase=_coerce_str(row.get("phase")),
                n_participants=_coerce_int(row.get("n_participants"), 0),
                summary=_coerce_str(row.get("summary")),
                outcomes_text=_coerce_str(row.get("outcomes_text")),
                status=_coerce_str(row.get("status")),
                sponsor=_coerce_str(row.get("sponsor")),
                start_date=_parse_date(row.get("start_date")),
                end_date=_parse_date(row.get("end_date")),
                extras=extras or None,
            )
            session.merge(trial)
            inserted += 1

        # Upsert registry row
        reg = session.get(DatasetRegistry, dataset_id)
        if reg is None:
            reg = DatasetRegistry(
                dataset_id=dataset_id,
                name=dataset_name or dataset_id,
                source_path=str(path),
                notes=notes,
                row_count=inserted,
                ingested_at=date.today(),
                mapping_json=mapping,
            )
        else:
            reg.name = dataset_name or reg.name
            reg.row_count = inserted
            reg.mapping_json = mapping
            reg.source_path = str(path)
            reg.notes = notes
            reg.ingested_at = date.today()
        session.merge(reg)
        session.commit()

    return inserted
