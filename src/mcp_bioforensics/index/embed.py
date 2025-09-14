"""Embedding utilities for MCP BioForensics.

Centralizes SentenceTransformer loading and text→vector functions.
- Cached model loader with env overrides
- Robust empty-input handling (uses correct embedding dim)
- Configurable trial→text concatenation
- Small helpers to clear/swap models for tests
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import torch
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from mcp_bioforensics.db.models import Trial

__all__ = [
    "get_model",
    "clear_model_cache",
    "embed_texts",
    "embed_trials",
    "trial_to_text",
]

# Environment-configurable defaults
_DEFAULT_MODEL_NAME = os.getenv("BIOFX_EMBED_MODEL", "all-MiniLM-L6-v2")
_DEVICE = os.getenv("BIOFX_DEVICE", None)  # "cuda" | "mps" | "cpu" | None→auto

# Lazily-initialized singleton cache
_MODEL: SentenceTransformer | None = None
_MODEL_NAME: str | None = None


def get_model(model_name: str | None = None) -> SentenceTransformer:
    """Return a cached SentenceTransformer instance.

    If ``model_name`` differs from the currently cached model, load and cache
    the requested one. Device selection defaults to auto unless BIOFX_DEVICE is set.
    """
    global _MODEL, _MODEL_NAME

    name = model_name or _DEFAULT_MODEL_NAME
    if _MODEL is not None and _MODEL_NAME == name:
        return _MODEL

    # Resolve device. Torch doesn't accept "auto"; pick best available.
    dev = _DEVICE
    if dev in (None, "", "auto"):
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            dev = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            dev = "mps"
        else:
            dev = "cpu"
    _MODEL = SentenceTransformer(name, device=dev)
    _MODEL_NAME = name
    return _MODEL


def clear_model_cache() -> None:
    """Clear the cached model (useful in tests)."""
    global _MODEL, _MODEL_NAME
    _MODEL = None
    _MODEL_NAME = None


def _embedding_dim(model: SentenceTransformer) -> int:
    """Return the sentence embedding dimension for the model."""
    try:
        dim = model.get_sentence_embedding_dimension()
        # Some typings may declare this as Optional[int]; guard explicitly.
        if isinstance(dim, int):
            return dim
        return 384
    except Exception:
        # Fallback for custom models or unexpected return types
        return 384


def embed_texts(
    texts: list[str] | tuple[str, ...],
    *,
    model_name: str | None = None,
    batch_size: int = 64,
    normalize: bool = True,
) -> NDArray[np.float32]:
    """Embed a sequence of texts into a float32 numpy array.

    Returns an array of shape (N, dim). If ``texts`` is empty, returns a
    zero-row array with the correct ``dim`` for the current model.
    """
    model = get_model(model_name)
    if not texts:
        dim = _embedding_dim(model)
        return np.empty((0, dim), dtype=np.float32)

    vectors = model.encode(
        list(texts),
        batch_size=batch_size,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    if vectors.dtype != np.float32:
        vectors = vectors.astype(np.float32)
    return vectors


@dataclass(slots=True)
class TrialTextConfig:
    include_summary: bool = True
    include_outcomes: bool = True


def trial_to_text(trial: Trial, cfg: TrialTextConfig | None = None) -> str:
    """Construct the text representation for a Trial row.

    You can tune which fields are included via ``cfg``.
    """
    cfg = cfg or TrialTextConfig()
    parts: list[str] = []
    if cfg.include_summary and getattr(trial, "summary", None):
        parts.append(str(trial.summary))
    if cfg.include_outcomes and getattr(trial, "outcomes_text", None):
        parts.append(str(trial.outcomes_text))
    return "\n".join(p for p in parts if p)


def embed_trials(
    session: Session,
    *,
    model_name: str | None = None,
    limit: int | None = None,
    batch_size: int = 64,
    normalize: bool = True,
    text_cfg: TrialTextConfig | None = None,
) -> tuple[list[str], NDArray[np.float32]]:
    """Embed trials from the database.

    Returns (trial_ids, vectors) where vectors has shape (N, dim).
    """
    q = session.query(Trial)
    if limit is not None:
        q = q.limit(int(limit))
    rows: list[Trial] = list(q)

    trial_ids = [r.trial_id for r in rows]
    texts = [trial_to_text(r, text_cfg) for r in rows]
    vectors = embed_texts(texts, model_name=model_name, batch_size=batch_size, normalize=normalize)
    return trial_ids, vectors


if __name__ == "__main__":  # pragma: no cover
    from mcp_bioforensics.db.session import SessionLocal

    with SessionLocal() as s:
        ids, vecs = embed_trials(s, limit=3)
        print({"count": len(ids), "shape": None if vecs.size == 0 else vecs.shape})
