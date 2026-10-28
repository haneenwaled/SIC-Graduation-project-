"""Local text embeddings.

* SentenceTransformerEmbedder - the real embedder (runs locally, no paid API).
* HashingEmbedder - deterministic, dependency-free; used by unit tests and as a clearly
  labelled offline fallback if the sentence-transformers model cannot be loaded.
"""
from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    name: str
    is_fallback: bool
    default_min_score: float

    def embed(self, texts: list[str], is_query: bool = False) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    is_fallback = False
    default_min_score = 0.2

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # imported lazily (heavy)

        self.name = model_name
        self._model = SentenceTransformer(model_name)
        try:  # multilingual MiniLM defaults to 128 tokens; its position embeddings allow more
            self._model.max_seq_length = max(self._model.max_seq_length or 0, 256)
        except Exception:
            pass
        # E5-family models need "query: " / "passage: " prefixes; other models need none.
        self._e5 = "e5" in model_name.lower()

    def embed(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if self._e5:
            prefix = "query: " if is_query else "passage: "
            texts = [prefix + t for t in texts]
        vecs = self._model.encode(texts, batch_size=64, show_progress_bar=False,
                                  normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vecs, dtype="float32")


_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    """Bag of word / word-bigram hashes projected to a fixed size, L2-normalised."""

    is_fallback = True
    default_min_score = 0.10

    def __init__(self, dim: int = 768, name: str = "hashing-fallback"):
        self.dim = dim
        self.name = name

    def _features(self, text: str) -> list[str]:
        toks = _TOKEN_RE.findall(text.lower())
        return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

    def embed(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for i, text in enumerate(texts):
            for feat in self._features(text):
                h = int.from_bytes(hashlib.md5(feat.encode()).digest()[:8], "little")
                out[i, h % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def get_embedder(model_name: str, allow_fallback: bool = True) -> tuple[Embedder, str | None]:
    """Return (embedder, warning). The warning is set when the fallback is used."""
    try:
        return SentenceTransformerEmbedder(model_name), None
    except Exception as exc:  # model download blocked, package missing, ...
        if not allow_fallback:
            raise
        warning = (
            f"Could not load embedding model '{model_name}' ({type(exc).__name__}). "
            "Using the offline keyword-hash fallback, so retrieval quality is lower. "
            "Check your internet connection (first run downloads the model) and restart."
        )
        return HashingEmbedder(), warning
