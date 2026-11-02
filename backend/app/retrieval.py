"""Corpus retrieval: filter chunks by code, rank by cosine similarity."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from app.config import BACKEND_DIR

CORPUS_DIR = BACKEND_DIR / "corpus"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def corpus() -> tuple[list[dict], np.ndarray]:
    chunks = json.loads((CORPUS_DIR / "chunks.json").read_text(encoding="utf-8"))
    emb = np.load(CORPUS_DIR / "embeddings.npy")
    return chunks, emb


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    try:  # use the cached copy; only download on the very first run
        return SentenceTransformer(EMBED_MODEL, local_files_only=True)
    except OSError:
        return SentenceTransformer(EMBED_MODEL)


def chunk_by_id() -> dict[str, dict]:
    return {c["id"]: c for c in corpus()[0]}


def embed(text: str) -> np.ndarray:
    return _model().encode([text], normalize_embeddings=True, show_progress_bar=False)[0]


def retrieve(code: str, remark: str, fix_path: str = "", k: int = 5) -> list[dict]:
    """Top-k chunks tagged with `code`, ranked by similarity to remark + fix path."""
    chunks, emb = corpus()
    idx = [i for i, c in enumerate(chunks) if code in c["codes"]]
    if not idx:
        return []
    q = embed(f"{remark} {fix_path}".strip())
    sims = emb[idx] @ q
    order = np.argsort(-sims)[:k]
    return [{**chunks[idx[j]], "score": float(sims[j])} for j in order]
