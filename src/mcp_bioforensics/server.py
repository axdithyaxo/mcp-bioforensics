from __future__ import annotations

import json
import os
import warnings
from typing import Any, cast

from fastmcp import FastMCP

from mcp_bioforensics.db.models import DatasetRegistry, Trial
from mcp_bioforensics.db.session import SessionLocal

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

os.environ.setdefault("FASTMCP_NO_BANNER", "1")

app = FastMCP("mcp-bioforensics")

# Reduce noisy SWIG/FAISS deprecation warnings that can clutter stdio transports
warnings.filterwarnings("ignore", message="builtin type SwigPy", category=DeprecationWarning)


@app.tool()  # type: ignore[misc]
def ping() -> dict[str, Any]:
    """Return a small JSON confirming the server is alive
    and reachable."""
    return {"ok": True, "service": "mcp-bioforensics"}


@app.tool()  # type: ignore[misc]
def list_datasets() -> list[dict[str, Any]]:
    """List all registered datasets with basic metadata:
    id, name, row count, ingestion time, and source path."""
    with SessionLocal() as s:
        rows = s.query(DatasetRegistry).order_by(DatasetRegistry.dataset_id).all()
        return [
            {
                "dataset_id": r.dataset_id,
                "name": r.name,
                "row_count": r.row_count,
                "ingested_at": str(r.ingested_at) if r.ingested_at else None,
                "source_path": r.source_path,
            }
            for r in rows
        ]


@app.tool()  # type: ignore[misc]
def get_trial(trial_id: str, dataset_id: str | None = None) -> dict[str, Any] | None:
    """Get one clinical trial by trial_id (and optional dataset_id).
    Return structured trial metadata, or null if not found."""
    with SessionLocal() as s:
        q = s.query(Trial).filter(Trial.trial_id == trial_id)
        if dataset_id:
            q = q.filter(Trial.dataset_id == dataset_id)
        t = q.first()
        if not t:
            return None
        return {
            "dataset_id": t.dataset_id,
            "trial_id": t.trial_id,
            "disease": t.disease,
            "phase": t.phase,
            "n_participants": t.n_participants,
            "status": t.status,
            "sponsor": t.sponsor,
            "start_date": str(t.start_date) if t.start_date else None,
            "end_date": str(t.end_date) if t.end_date else None,
            "summary": t.summary,
            "outcomes_text": t.outcomes_text,
        }


# Shared normalizer for optional string-like fields
def _norm_str(x: Any) -> str | None:
    if x is None:
        return None
    xs = str(x).strip()
    if xs == "" or xs.lower() in {"null", "none"}:
        return None
    return xs


# Canonicalize many phase variants to tokens like PHASE3, PHASE2|PHASE3, EARLY_PHASE1
def _canon_phase(x: Any) -> str | None:
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in {"", "null", "none"}:
        return None
    mapping = {
        # simple numbers and words
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
        # combos
        "1/2": "PHASE1|PHASE2",
        "phase 1/2": "PHASE1|PHASE2",
        "i/ii": "PHASE1|PHASE2",
        "2/3": "PHASE2|PHASE3",
        "phase 2/3": "PHASE2|PHASE3",
        "ii/iii": "PHASE2|PHASE3",
        # special
        "early phase 1": "EARLY_PHASE1",
    }
    return mapping.get(s, s.upper())


# -- Small helpers to keep payload parsing simple and lint-friendly --


def _payload_to_dict(payload: Any) -> dict[str, Any] | None:
    """Accept a dict or a JSON string and return a dict, else None."""
    if isinstance(payload, str):
        try:
            return cast(dict[str, Any], json.loads(payload))
        except Exception:
            return None
    if isinstance(payload, dict):
        return payload
    return None


def _merge_options(d: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Extract query and a merged options dict from a payload dict."""
    q = d.get("query")
    if not isinstance(q, str) or not q.strip():
        return "", {}

    opts: dict[str, Any] = d.get("options") or {}
    if not isinstance(opts, dict):
        opts = {}

    # Merge any top-level optional keys not present in options
    for k in ("phase", "disease", "status", "min_participants", "top_k"):
        if k in d and k not in opts:
            opts[k] = d[k]

    return q.strip(), opts


def _parse_payload(payload: Any) -> tuple[str, str | None, str | None, str | None, int | None, int]:
    d = _payload_to_dict(payload)
    if d is None:
        return "", None, None, None, None, 10

    query, opts = _merge_options(d)
    if not query:
        return "", None, None, None, None, 10

    phase = _canon_phase(opts.get("phase"))
    disease = _norm_str(opts.get("disease"))
    status = _norm_str(opts.get("status"))

    # Coerce numeric-like values with explicit fallbacks
    mp = opts.get("min_participants")
    if isinstance(mp, int):
        min_participants: int | None = mp
    else:
        try:
            min_participants = int(mp) if mp is not None and str(mp).strip() != "" else None
        except Exception:
            min_participants = None  # non-integer, ignore filter

    tk = opts.get("top_k", 10)
    try:
        top_k = int(tk)
    except Exception:
        top_k = 10

    return query, phase, disease, status, min_participants, top_k


@app.tool()  # type: ignore[misc]
def search_trials(payload: Any) -> list[dict[str, Any]]:
    """Permissive search over trials via a single JSON `payload`.

    Payload (dict or JSON string):
      - query: str (required)
      - options: dict (optional) with keys {phase, disease, status, min_participants, top_k}
      - Top-level keys {phase, disease, status, min_participants, top_k} are also accepted
        and merged into `options`.

    Notes
    -----
    - `phase` is normalized to canonical codes: PHASE1, PHASE2, PHASE3, PHASE4, EARLY_PHASE1,
      or combos like PHASE1|PHASE2, PHASE2|PHASE3. Variants like "Phase 3", "III" are accepted.
    - Returns a ranked list of trials with fields:
      dataset_id, trial_id, score, disease, phase, n_participants.
    """
    query, phase, disease, status, min_participants, top_k = _parse_payload(payload)

    if not query:
        return []

    from mcp_bioforensics.retrieval.hybrid import hybrid_search

    results = hybrid_search(
        query,
        phase=phase,
        disease=disease,
        min_participants=min_participants,
        status=status,
        top_k=top_k,
    )

    if phase:
        want = set(str(phase).upper().split("|"))
        results = [r for r in results if r.phase and set(str(r.phase).upper().split("|")) & want]

    return [
        {
            "dataset_id": r.dataset_id,
            "trial_id": r.trial_id,
            "score": r.score,
            "disease": r.disease,
            "phase": r.phase,
            "n_participants": r.n_participants,
        }
        for r in results
    ]


@app.tool()  # type: ignore[misc]
def build_vector_index() -> dict[str, Any]:
    """Rebuild the FAISS vector index from all trials in the DB.
    Return index stats (dim, count, file path)."""
    from mcp_bioforensics.index.faiss_store import (
        build_index,
    )  # local import to avoid FAISS import on startup

    with SessionLocal() as s:
        stats = build_index(s)
        return {"dim": stats.dim, "count": stats.count, "index_path": stats.index_path}


@app.prompt("trial-rag")  # type: ignore[misc]
def trial_rag(
    query: str,
    *,
    phase: str | None = None,
    disease: str | None = None,
    min_participants: int | None = None,
    status: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Build a context-rich prompt for the assistant by retrieving the most relevant trials
    (semantic + filters) and packaging them as messages.

    Canonical phases: PHASE1, PHASE2, PHASE3, PHASE4, EARLY_PHASE1, or combos like PHASE2|PHASE3.
    """

    # Normalize inputs using your existing helpers
    ph = _canon_phase(phase)
    dz = _norm_str(disease)
    st = _norm_str(status)

    # Clamp top_k for stability
    try:
        top_k = int(top_k)
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 25))

    # Retrieve context
    try:
        from mcp_bioforensics.retrieval.hybrid import hybrid_search

        hits = hybrid_search(
            query,
            phase=ph,
            disease=dz,
            min_participants=min_participants,
            status=st,
            top_k=top_k,
        )
    except Exception as e:
        # Return a minimal prompt on failure (never crash stdio)
        return {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a clinical trials assistant. The retrieval layer failed.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Query: {query}\n\n"
                        f"(Note: retrieval error: {e})\n"
                        "Answer with general guidance."
                    ),
                },
            ]
        }

    # Format a compact, token-safe context block
    rows = []
    for r in hits[:top_k]:
        rows.append(
            f"- trial_id: {r.trial_id} | disease: {r.disease or ''} | "
            f"phase: {r.phase or ''} | n: {r.n_participants or ''} | score: {round(r.score, 3)}"
        )
    context_block = "\n".join(rows) if rows else "(no matching trials found)"

    # Return an MCP Prompt (messages array). Clients will use this directly.
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful clinical trials assistant. Use only the provided context. "
                    "If evidence is missing, say so. Prefer concise, structured answers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context (top {len(rows)} trials):\n{context_block}\n\n"
                    "Question: "
                    f"{query}\n\n"
                    "Instructions:\n"
                    "- Summarize the most relevant trials and why they match.\n"
                    "- Note phases, sample sizes, and any clear endpoints.\n"
                    "- Offer next-step filters (e.g., PHASE3, n>=100, date ranges).\n"
                ),
            },
        ]
    }


def run() -> None:
    app.run()


if __name__ == "__main__":
    run()
