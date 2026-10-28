"""Heading-aware chunking for Markdown documents; one chunk per catalog product."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import CATALOG_DOC_TYPE
from .document_loader import SourceDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Chunk:
    chunk_id: str
    text: str            # text shown to the user / sent to the LLM
    source: str
    doc_type: str
    section: str = ""    # heading path, e.g. "5. Customer Prioritization > 5.5 Focus List"
    metadata: dict = field(default_factory=dict)

    @property
    def embed_text(self) -> str:
        """Text that is embedded: section context + body (helps short chunks retrieve well)."""
        prefix = f"{self.source} | {self.section}\n" if self.section else f"{self.source}\n"
        return prefix + self.text


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Return (heading_path, body) pairs. Code fences are never treated as headings."""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        body = "\n".join(buf).strip()
        # A heading with no body of its own is kept in the buffer so it merges into the next section.
        if body and all(HEADING_RE.match(ln) for ln in body.splitlines() if ln.strip()):
            return
        if body:
            sections.append((" > ".join(h for _, h in stack), body))
        buf.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        buf.append(line)  # heading line stays inside its own chunk text
    flush()
    if buf and not sections:
        sections.append(("", "\n".join(buf).strip()))
    return sections


def _pack(body: str, size: int, overlap: int) -> list[str]:
    """Pack blocks (paragraphs/tables/lines) into pieces <= size chars with overlap."""
    if len(body) <= size:
        return [body]
    blocks: list[str] = []
    for para in re.split(r"\n\s*\n", body):
        if len(para) <= size:
            blocks.append(para)
        else:  # oversized block (long table/list): split by line, then hard-split
            for line in para.split("\n"):
                while len(line) > size:
                    blocks.append(line[:size])
                    line = line[size:]
                blocks.append(line)
    pieces: list[str] = []
    cur = ""
    for blk in blocks:
        sep = "\n\n" if cur else ""
        if cur and len(cur) + len(sep) + len(blk) > size:
            pieces.append(cur)
            tail = cur[-overlap:] if overlap > 0 else ""
            if tail and " " in tail:  # start the overlap at a word boundary
                tail = tail.split(" ", 1)[1]
            cur = (tail + "\n" + blk) if tail else blk
        else:
            cur = cur + sep + blk
    if cur.strip():
        pieces.append(cur)
    return pieces


def chunk_markdown(doc: SourceDocument, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    chunks: list[Chunk] = []
    for section, body in _split_sections(doc.text):
        for piece in _pack(body, chunk_size, chunk_overlap):
            n = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}::{n:04d}", text=piece.strip(), source=doc.source,
                doc_type=doc.doc_type, section=section or doc.source,
                metadata={"chunk_index": n},
            ))
    return chunks


def chunk_documents(docs: list[SourceDocument], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        if doc.doc_type == CATALOG_DOC_TYPE:
            chunks.append(Chunk(
                chunk_id=f"catalog::{doc.doc_id}", text=doc.text, source=doc.source,
                doc_type=CATALOG_DOC_TYPE, section=f"Product {doc.metadata.get('product_id', doc.doc_id)}",
                metadata=dict(doc.metadata),
            ))
        else:
            chunks.extend(chunk_markdown(doc, chunk_size, chunk_overlap))
    return chunks
