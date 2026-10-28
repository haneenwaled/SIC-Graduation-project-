"""FAISS vector store with an on-disk cache that is invalidated when sources change."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np

from .chunking import Chunk
from .embeddings import Embedder

INDEX_FORMAT_VERSION = 2  # bump when chunking/embedding text logic changes


def compute_fingerprint(files: list[Path], chunk_size: int, chunk_overlap: int, embedder_name: str) -> str:
    """Hash of source file contents + chunk settings + embedder -> detects stale indexes."""
    h = hashlib.sha256()
    h.update(f"v{INDEX_FORMAT_VERSION}|{chunk_size}|{chunk_overlap}|{embedder_name}".encode())
    for p in sorted(Path(f) for f in files):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


class VectorStore:
    def __init__(self, index: faiss.Index, chunks: list[Chunk], fingerprint: str = ""):
        self.index = index
        self.chunks = chunks
        self.fingerprint = fingerprint

    # ---- build / persist -------------------------------------------------
    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder, fingerprint: str = "") -> "VectorStore":
        if not chunks:
            raise ValueError("Cannot build an index from zero chunks")
        vecs = embedder.embed([c.embed_text for c in chunks]).astype("float32")
        index = faiss.IndexFlatIP(vecs.shape[1])  # cosine similarity (vectors are normalised)
        index.add(vecs)
        return cls(index, chunks, fingerprint)

    def save(self, cache_dir: Path) -> None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(cache_dir / "index.faiss"))
        (cache_dir / "chunks.json").write_text(
            json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False), encoding="utf-8")
        (cache_dir / "manifest.json").write_text(
            json.dumps({"fingerprint": self.fingerprint, "n_chunks": len(self.chunks)}), encoding="utf-8")

    @classmethod
    def load_if_fresh(cls, cache_dir: Path, fingerprint: str) -> "VectorStore | None":
        """Load the cached index only if its fingerprint matches; otherwise return None."""
        cache_dir = Path(cache_dir)
        try:
            manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("fingerprint") != fingerprint:
                return None
            index = faiss.read_index(str(cache_dir / "index.faiss"))
            raw = json.loads((cache_dir / "chunks.json").read_text(encoding="utf-8"))
            chunks = [Chunk(**r) for r in raw]
            if index.ntotal != len(chunks):
                return None
            return cls(index, chunks, fingerprint)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            return None

    # ---- search ----------------------------------------------------------
    def search(self, query_vec: np.ndarray, top_k: int, doc_types: tuple[str, ...] | None = None
               ) -> list[tuple[Chunk, float]]:
        """Top-k by cosine similarity, optionally restricted by doc_type metadata."""
        n = self.index.ntotal
        if n == 0:
            return []
        q = np.asarray(query_vec, dtype="float32").reshape(1, -1)
        k = n if doc_types else min(top_k, n)  # flat index: full scan is cheap, then filter
        scores, ids = self.index.search(q, k)
        hits: list[tuple[Chunk, float]] = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            chunk = self.chunks[idx]
            if doc_types and chunk.doc_type not in doc_types:
                continue
            hits.append((chunk, float(score)))
            if len(hits) >= top_k:
                break
        return hits
