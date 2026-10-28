"""Retrieval over the vector store: knowledge documents vs. product catalog stay separate."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .chunking import Chunk
from .config import CATALOG_DOC_TYPE, KNOWLEDGE_DOC_TYPES
from .embeddings import Embedder
from .vector_store import VectorStore

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "of", "and", "or", "to", "for", "in", "on", "with", "is", "are", "what",
         "which", "find", "show", "me", "products", "product", "items", "item", "catalog", "matching",
         "any", "that", "do", "we", "have", "list", "about", "related"}


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder, top_k: int = 6, min_score: float | None = None):
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = embedder.default_min_score if min_score is None else min_score

    def _search(self, query: str, doc_types: tuple[str, ...], top_k: int) -> list[RetrievedChunk]:
        qv = self.embedder.embed([query], is_query=True)[0]
        return [RetrievedChunk(c, s) for c, s in self.store.search(qv, top_k, doc_types)]

    def retrieve_knowledge(self, query: str, doc_types: tuple[str, ...] | None = None,
                           top_k: int | None = None) -> list[RetrievedChunk]:
        """Policy / playbook / KPI passages above the relevance threshold."""
        types = tuple(doc_types) if doc_types else KNOWLEDGE_DOC_TYPES
        hits = self._search(query, types, top_k or self.top_k)
        return [h for h in hits if h.score >= self.min_score]

    def retrieve_products(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        """Catalog products: semantic score blended with exact keyword overlap on the text."""
        terms = {w for w in _WORD.findall(query.lower()) if w not in _STOP and len(w) > 1}
        pool = self._search(query, (CATALOG_DOC_TYPE,), max(top_k * 5, 40))
        rescored: list[RetrievedChunk] = []
        for h in pool:
            text_words = set(_WORD.findall(h.chunk.text.lower()))
            overlap = len(terms & text_words) / len(terms) if terms else 0.0
            rescored.append(RetrievedChunk(h.chunk, 0.7 * h.score + 0.3 * overlap))
        rescored.sort(key=lambda r: (-r.score, r.chunk.chunk_id))
        # exact keyword hits are always relevant; otherwise require the semantic threshold
        return [r for r in rescored if r.score >= self.min_score][:top_k]

    def lookup_product_id(self, product_id: str) -> RetrievedChunk | None:
        """Deterministic exact lookup by catalog product id."""
        for c in self.store.chunks:
            if c.doc_type == CATALOG_DOC_TYPE and str(c.metadata.get("product_id")) == str(product_id):
                return RetrievedChunk(c, 1.0)
        return None
