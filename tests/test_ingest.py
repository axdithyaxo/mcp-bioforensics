from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mcp_bioforensics.db.models import Base, Trial
from mcp_bioforensics.ingest.loaders import ingest_csv

def test_ingest_csv(tmp_path):
    # Temporary CSV
    csvp = tmp_path / "sample.csv"
    csvp.write_text(
        "trial_id,disease,phase,n_participants,summary,outcomes_text,status,sponsor,start_date,end_date\n"
        "NCT1,Glioblastoma,II,100,Trial,PFS Completed,completed,NIH,2020-01-01,2021-01-01\n"
    )

    # Use an in-memory SQLite engine for isolation
    test_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(test_engine)

    # Monkeypatch the loader to use this engine
    from mcp_bioforensics.db import session as db_session
    db_session.engine = test_engine
    db_session.SessionLocal.configure(bind=test_engine)

    n = ingest_csv(str(csvp))
    assert n == 1

    with Session(test_engine) as s:
        assert s.query(Trial).count() == 1