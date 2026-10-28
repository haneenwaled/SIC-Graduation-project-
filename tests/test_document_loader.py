import json

import pytest

from src.chunking import chunk_documents, chunk_markdown
from src.document_loader import (MissingFilesError, check_required_files, load_all_documents,
                                 load_catalog, load_markdown)


def test_load_all_documents_types_and_counts(data_dir):
    report = load_all_documents(data_dir)
    types = [d.doc_type for d in report.documents]
    assert types.count("product_catalog") == 3
    assert {"retention_playbook", "promotion_policy", "business_rules"} <= set(types)
    assert report.catalog_skipped == 0


def test_missing_file_reports_exact_filename(data_dir):
    (data_dir / "promotion_policy.md").unlink()
    with pytest.raises(MissingFilesError) as exc:
        load_all_documents(data_dir)
    assert "promotion_policy.md" in str(exc.value)
    assert exc.value.missing == ["promotion_policy.md"]
    assert check_required_files(data_dir) == ["promotion_policy.md"]


def test_empty_markdown_rejected(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("   \n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_markdown(p, "business_rules")


def test_catalog_bad_and_duplicate_lines_skipped_and_reported(tmp_path):
    p = tmp_path / "c.jsonl"
    good = {"id": "1", "text": "Product ID: 1", "metadata": {"product_id": "1"}}
    p.write_text("\n".join([json.dumps(good), "not json", json.dumps({"id": "2"}), json.dumps(good)]), encoding="utf-8")
    docs, skipped, warnings = load_catalog(p)
    assert len(docs) == 1 and skipped == 3 and warnings


def test_markdown_chunks_have_metadata_and_section_headings(data_dir):
    doc = load_markdown(data_dir / "retention_playbook.md", "retention_playbook")
    chunks = chunk_markdown(doc, 400, 50)
    assert chunks
    for c in chunks:
        assert c.source == "retention_playbook.md" and c.doc_type == "retention_playbook"
        assert c.chunk_id.startswith("retention_playbook::") and c.section
    high = [c for c in chunks if "Personal outreach" in c.text][0]
    assert high.section.endswith("3.3 High Risk") and "3. Recommended Actions" in high.section


def test_chunk_size_and_overlap_are_respected():
    from src.document_loader import SourceDocument
    text = "# T\n\n" + "\n\n".join(f"Paragraph {i} " + "word " * 30 for i in range(20))
    chunks = chunk_markdown(SourceDocument(text, "t.md", "business_rules", "t"), 300, 60)
    assert len(chunks) > 3
    assert all(len(c.text) <= 300 + 60 + 5 for c in chunks)
    with pytest.raises(ValueError):
        chunk_markdown(SourceDocument(text, "t.md", "business_rules", "t"), 100, 100)


def test_headings_inside_code_fences_are_not_split():
    from src.document_loader import SourceDocument
    text = "# Title\n\n## Real\n\n```\n# not a heading\n```\n\ntext"
    chunks = chunk_markdown(SourceDocument(text, "t.md", "business_rules", "t"), 500, 50)
    assert all("not a heading" not in c.section for c in chunks)


def test_catalog_documents_become_one_chunk_each(data_dir):
    chunks = chunk_documents(load_all_documents(data_dir).documents, 400, 50)
    cat = [c for c in chunks if c.doc_type == "product_catalog"]
    assert len(cat) == 3 and cat[0].metadata["product_id"] == "10001"
    assert cat[0].source == "product_catalog_documents.jsonl"
