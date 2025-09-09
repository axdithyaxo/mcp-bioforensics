from sqlalchemy.orm import Session
from mcp_bioforensics.ingest.loaders import ingest_csv
from mcp_bioforensics.db.session import engine
from mcp_bioforensics.db.models import Base, Trial

def test_ingest_csv(tmp_path):
    csvp = tmp_path / "sample.csv"
    csvp.write_text(
        "trial_id,disease,phase,n_participants,summary,outcomes_text,status,sponsor,start_date,end_date\n"
        "NCT1,Glioblastoma,II,100,Trial,PFS Completed,completed,NIH,2020-01-01,2021-01-01\n"
    )
    Base.metadata.create_all(engine)
    n = ingest_csv(str(csvp))
    assert n == 1
    with Session(engine) as s:
        assert s.query(Trial).count() == 1
