"""Load and validate the Markdown knowledge documents and the JSONL product catalog."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import CATALOG_DOC_TYPE, CATALOG_FILE, MARKDOWN_FILES, REQUIRED_FILES


class MissingFilesError(FileNotFoundError):
    """Raised when required input files are not in the data folder."""

    def __init__(self, missing: list[str], data_dir: Path):
        self.missing = missing
        self.data_dir = data_dir
        super().__init__(
            "Missing required input file(s): " + ", ".join(missing)
            + f". Place them in: {data_dir}"
        )


@dataclass
class SourceDocument:
    """One loaded unit of source text (a Markdown file or one catalog product)."""

    text: str
    source: str          # filename
    doc_type: str        # retention_playbook | promotion_policy | business_rules | product_catalog
    doc_id: str          # unique id inside the source
    metadata: dict = field(default_factory=dict)


@dataclass
class LoadReport:
    documents: list[SourceDocument]
    catalog_skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def check_required_files(data_dir: Path, names: list[str] | None = None) -> list[str]:
    """Return the names of required files that are absent from ``data_dir``."""
    return [n for n in (names or REQUIRED_FILES) if not (Path(data_dir) / n).is_file()]


def load_markdown(path: Path, doc_type: str) -> SourceDocument:
    text = Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"{Path(path).name} is empty")
    return SourceDocument(text=text, source=Path(path).name, doc_type=doc_type, doc_id=Path(path).stem)


def load_catalog(path: Path) -> tuple[list[SourceDocument], int, list[str]]:
    """Parse the JSONL catalog. Invalid lines are skipped and reported, never invented."""
    docs: list[SourceDocument] = []
    skipped = 0
    warnings: list[str] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                text = str(rec["text"]).strip()
                doc_id = str(rec["id"])
                if not text:
                    raise ValueError("empty text")
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                skipped += 1
                if len(warnings) < 5:
                    warnings.append(f"{Path(path).name} line {line_no} skipped: {exc}")
                continue
            if doc_id in seen:
                skipped += 1
                if len(warnings) < 5:
                    warnings.append(f"{Path(path).name} line {line_no}: duplicate id {doc_id} skipped")
                continue
            seen.add(doc_id)
            meta = rec.get("metadata") or {}
            docs.append(SourceDocument(
                text=text, source=Path(path).name, doc_type=CATALOG_DOC_TYPE, doc_id=doc_id,
                metadata={"product_id": meta.get("product_id", doc_id), "origin": meta.get("source", "")},
            ))
    if skipped > 5:
        warnings.append(f"{skipped} catalog lines were skipped in total.")
    return docs, skipped, warnings


def load_all_documents(data_dir: Path) -> LoadReport:
    """Load every knowledge document. Raises MissingFilesError naming the exact missing files."""
    data_dir = Path(data_dir)
    missing = check_required_files(data_dir, [*MARKDOWN_FILES, CATALOG_FILE])
    if missing:
        raise MissingFilesError(missing, data_dir)
    docs = [load_markdown(data_dir / name, dtype) for name, dtype in MARKDOWN_FILES.items()]
    catalog, skipped, warnings = load_catalog(data_dir / CATALOG_FILE)
    if not catalog:
        raise ValueError(f"{CATALOG_FILE} contains no valid product records")
    return LoadReport(documents=docs + catalog, catalog_skipped=skipped, warnings=warnings)
