import pandas as pd

from mcp_bioforensics.db.models import Base, Trial
from mcp_bioforensics.db.session import SessionLocal, engine


def _normalize_phase(phase: str) -> str:
    if not isinstance(phase, str):
        return ""
    return phase.strip().upper().replace("PHASE ", "")


def _normalize_status(status: str) -> str:
    if not isinstance(status, str):
        return ""
    return status.strip().capitalize()


def ingest_csv(path: str) -> int:
    """Ingest CSV into DB, returns number of rows inserted/merged."""
    df = pd.read_csv(path)

    if "phase" in df.columns:
        df["phase"] = df["phase"].apply(_normalize_phase)
    if "status" in df.columns:
        df["status"] = df["status"].apply(_normalize_status)

    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        for _, row in df.iterrows():
            trial = Trial(
                trial_id=row["trial_id"],
                disease=row.get("disease", ""),
                phase=row.get("phase", ""),
                n_participants=int(row.get("n_participants", 0))
                if pd.notna(row.get("n_participants", 0))
                else 0,
                summary=row.get("summary", ""),
                outcomes_text=row.get("outcomes_text", ""),
                status=row.get("status", ""),
                sponsor=row.get("sponsor", ""),
                start_date=None,
                end_date=None,
            )
            session.merge(trial)  # upsert behavior
        session.commit()
    return len(df)
