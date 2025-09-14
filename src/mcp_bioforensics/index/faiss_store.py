"""FAISS index utilities for MCP BioForensics.

Builds a vector index over Trial rows (summary + outcomes_text) using
Sentence-Transformers embeddings. Persists the index to disk along with a
sidecar ID mapping so we can resolve FAISS internal ids back to trial_id.

Environment variables:
- BIOFX_INDEX_PATH: path to the FAISS index file (default: index/faiss.index)
- BIOFX_EMBED_MODEL: embedding model name (forwarded to embed.get_model)
- BIOFX_DEVICE: device override for embeddings (cpu/cuda/mps)
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

try:  # pragma: no cover - import guard
    import faiss
except Exception as exc:  # pragma: no cover - helpful error
    raise ImportError(
        "faiss is required. Install the optional extra: `poetry install -E vector`"
    ) from exc

from sqlalchemy.orm import Session

from mcp_bioforensics.index.embed import embed_texts, embed_trials

DEFAULT_INDEX_PATH = os.getenv("BIOFX_INDEX_PATH", "index/faiss.index")
DEFAULT_IDS_PATH = str(Path(DEFAULT_INDEX_PATH).with_suffix(".ids.json"))


@dataclass
class IndexStats:
    dim: int
    count: int
    index_path: str
    ids_path: str


def _ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _l2_normalize(vectors: NDArray[np.float32]) -> NDArray[np.float32]:
    """L2-normalize a 2D array of vectors to unit length."""
    norms: NDArray[np.float32] = np.linalg.norm(vectors, axis=1, keepdims=True).astype(np.float32)
    norms[norms == 0] = 1.0
    normalized: NDArray[np.float32] = (vectors / norms).astype(np.float32)
    return normalized


def build_index(
    session: Session,
    *,
    index_path: str | None = None,
    ids_path: str | None = None,
    model_name: str | None = None,
    limit: int | None = None,
) -> IndexStats:
    """Build a FAISS index from trials in the database and save to disk.

    Returns basic stats including dimension and number of vectors.
    """
    idx_path = index_path or DEFAULT_INDEX_PATH
    idp_path = ids_path or DEFAULT_IDS_PATH

    trial_ids, vectors = embed_trials(session, model_name=model_name, limit=limit)
    if vectors.size == 0:
        # Create an empty index with a default dimension (use 384 for MiniLM)
        dim = 384
        index = faiss.IndexFlatIP(dim)
        _ensure_parent_dir(idx_path)
        faiss.write_index(index, str(idx_path))
        Path(idp_path).write_text(json.dumps([]))
        return IndexStats(dim=dim, count=0, index_path=str(idx_path), ids_path=str(idp_path))

    vectors = _l2_normalize(vectors.astype(np.float32))
    dim = vectors.shape[1]

    index = faiss.IndexFlatIP(dim)  # cosine sim with normalized vectors
    index.add(vectors)

    _ensure_parent_dir(idx_path)
    faiss.write_index(index, str(idx_path))
    Path(idp_path).write_text(json.dumps(trial_ids, indent=2))

    return IndexStats(
        dim=dim, count=len(trial_ids), index_path=str(idx_path), ids_path=str(idp_path)
    )


@dataclass
class LoadedIndex:
    index: Any
    ids: list[str]


def load_index(index_path: str | None = None, ids_path: str | None = None) -> LoadedIndex:
    idx_path = index_path or DEFAULT_INDEX_PATH
    idp_path = ids_path or DEFAULT_IDS_PATH
    if not Path(idx_path).exists():
        raise FileNotFoundError(f"FAISS index not found at {idx_path}. Run `biofx index` first.")
    if not Path(idp_path).exists():
        raise FileNotFoundError(f"ID mapping not found at {idp_path}. Run `biofx index` first.")

    index = faiss.read_index(str(idx_path))
    ids: list[str] = json.loads(Path(idp_path).read_text())
    return LoadedIndex(index=index, ids=ids)


def search_texts(
    query_texts: Sequence[str],
    top_k: int = 5,
    *,
    index_path: str | None = None,
    ids_path: str | None = None,
    model_name: str | None = None,
) -> list[list[tuple[str, float]]]:
    """Search the FAISS index with one or more query strings.

    Returns a list (one per query) of (trial_id, score) pairs sorted by score desc.
    """
    li = load_index(index_path=index_path, ids_path=ids_path)

    qvecs = embed_texts(list(query_texts), model_name=model_name)
    if qvecs.size == 0:
        return [[] for _ in query_texts]
    qvecs = _l2_normalize(qvecs.astype(np.float32))

    scores, indices = li.index.search(qvecs, top_k)
    results: list[list[tuple[str, float]]] = []
    for row_scores, row_indices in zip(scores, indices, strict=False):
        pairs: list[tuple[str, float]] = []
        for idx, sc in zip(row_indices, row_scores, strict=False):
            if idx == -1:
                continue
            trial_id = li.ids[idx] if 0 <= idx < len(li.ids) else ""
            pairs.append((trial_id, float(sc)))
        results.append(pairs)
    return results


def search_one(query_text: str, top_k: int = 5, **kwargs: Any) -> list[tuple[str, float]]:
    """Convenience wrapper for single-query search."""
    return search_texts([query_text], top_k=top_k, **kwargs)[0]
