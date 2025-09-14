from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from mcp_bioforensics.db.models import Trial
from mcp_bioforensics.db.session import SessionLocal
from mcp_bioforensics.index.faiss_store import search_texts


@dataclass(slots=True)
class HybridResult:
    dataset_id: str
    trial_id: str
    disease: str
    phase: str
    n_participants: int
    score: float


def _parse_sid_tid(raw_id: str | Any) -> tuple[str | None, str]:
    """Split ids of the form "dataset_id:trial_id"; fall back to only trial_id."""
    s = str(raw_id)
    if ":" in s:
        ds, tid = s.split(":", 1)
        return ds, tid
    return None, s


def _matches_filters(
    t: Trial,
    *,
    phase: str | None = None,
    disease: str | None = None,
    min_participants: int | None = None,
    status: str | None = None,
) -> bool:
    if phase and (t.phase or "").upper() != str(phase).upper():
        return False
    if disease and (disease.lower() not in (t.disease or "").lower()):
        return False
    if min_participants is not None and (t.n_participants or 0) < int(min_participants):
        return False
    if status and (status.lower() not in (t.status or "").lower()):
        return False
    return True


def _fetch_trial(session: Session, raw_id: str) -> Trial | None:
    dsid, tid = _parse_sid_tid(raw_id)
    stmt = select(Trial).where(Trial.trial_id == tid)
    if dsid:
        stmt = stmt.where(Trial.dataset_id == dsid)
    res = session.execute(stmt).scalar_one_or_none()
    return cast(Trial | None, res)


def hybrid_search(
    query: str,
    *,
    phase: str | None = None,
    disease: str | None = None,
    min_participants: int | None = None,
    status: str | None = None,
    top_k: int = 10,
) -> list[HybridResult]:
    """Hybrid retrieval: FAISS semantic search + SQL-like filters.

    Strategy:
    - Run FAISS search with a widened beam (top_k * 5) to get candidates.
    - Resolve each id to a Trial row and apply structured filters.
    - Return the top_k remaining results, preserving FAISS score ordering.

    Note: If the FAISS sidecar ids are of the form "dataset_id:trial_id",
    results remain unambiguous across datasets. If they are plain trial ids,
    we resolve against the DB and return the first match found.
    """
    beam = max(top_k * 5, 20)
    faiss_lists = search_texts([query], top_k=beam)
    if not faiss_lists:
        return []

    candidates = faiss_lists[0]
    results: list[HybridResult] = []

    with SessionLocal() as s:
        for raw_id, score in candidates:
            trial = _fetch_trial(s, raw_id)
            if not trial:
                continue
            if not _matches_filters(
                trial,
                phase=phase,
                disease=disease,
                min_participants=min_participants,
                status=status,
            ):
                continue
            results.append(
                HybridResult(
                    dataset_id=trial.dataset_id,
                    trial_id=trial.trial_id,
                    disease=trial.disease or "",
                    phase=trial.phase or "",
                    n_participants=trial.n_participants or 0,
                    score=float(score),
                )
            )
            if len(results) >= top_k:
                break

    return results
