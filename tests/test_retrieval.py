from src.chunking import chunk_documents
from src.document_loader import load_all_documents
from src.rag_engine import build_engine
from src.retriever import Retriever
from src.vector_store import VectorStore, compute_fingerprint


def _store(data_dir, embedder, fp="fp"):
    chunks = chunk_documents(load_all_documents(data_dir).documents, 400, 50)
    return VectorStore.build(chunks, embedder, fp), chunks


def test_knowledge_retrieval_returns_correct_source_metadata(data_dir, embedder):
    store, _ = _store(data_dir, embedder)
    r = Retriever(store, embedder, top_k=3, min_score=0.0)
    hits = r.retrieve_knowledge("what outreach for high risk customers")
    assert hits[0].chunk.source == "retention_playbook.md"
    assert hits[0].chunk.doc_type == "retention_playbook"
    assert hits[0].chunk.section.endswith("3.3 High Risk")
    assert all(h.chunk.doc_type != "product_catalog" for h in hits)


def test_doc_type_filter_isolates_promotion_policy(data_dir, embedder):
    store, _ = _store(data_dir, embedder)
    r = Retriever(store, embedder, top_k=5, min_score=0.0)
    hits = r.retrieve_knowledge("approval of promotions", doc_types=("promotion_policy",))
    assert hits and {h.chunk.source for h in hits} == {"promotion_policy.md"}


def test_product_retrieval_is_catalog_only_and_finds_keyword_match(data_dir, embedder):
    store, _ = _store(data_dir, embedder)
    r = Retriever(store, embedder, top_k=3, min_score=0.0)
    hits = r.retrieve_products("wrapping tape")
    assert hits[0].chunk.metadata["product_id"] == "10001"
    assert {h.chunk.doc_type for h in hits} == {"product_catalog"}
    assert r.lookup_product_id("10003").chunk.text.startswith("Product ID: 10003")
    assert r.lookup_product_id("nope") is None


def test_min_score_filters_irrelevant_results(data_dir, embedder):
    store, _ = _store(data_dir, embedder)
    r = Retriever(store, embedder, top_k=3, min_score=0.99)
    assert r.retrieve_knowledge("zzzz qqqq") == []


def test_index_cache_roundtrip_and_stale_detection(data_dir, embedder, tmp_path):
    store, _ = _store(data_dir, embedder, "abc")
    store.save(tmp_path / "idx")
    assert VectorStore.load_if_fresh(tmp_path / "idx", "abc") is not None
    assert VectorStore.load_if_fresh(tmp_path / "idx", "different") is None   # stale -> rebuild
    assert VectorStore.load_if_fresh(tmp_path / "nothing", "abc") is None


def test_fingerprint_changes_when_source_changes(data_dir):
    files = [data_dir / "retention_playbook.md", data_dir / "promotion_policy.md"]
    a = compute_fingerprint(files, 400, 50, "e")
    (data_dir / "promotion_policy.md").write_text("# changed\n\ntext", encoding="utf-8")
    assert compute_fingerprint(files, 400, 50, "e") != a
    assert compute_fingerprint(files, 500, 50, "e") != compute_fingerprint(files, 400, 50, "e")


def test_build_engine_reuses_cache_then_rebuilds_after_change(config, embedder, fake_llm):
    _, s1 = build_engine(config, embedder=embedder, llm=fake_llm)
    assert s1.index_state.startswith("rebuilt")
    _, s2 = build_engine(config, embedder=embedder, llm=fake_llm)
    assert s2.index_state == "loaded from cache"
    (config.data_dir / "retention_playbook.md").write_text("# New\n\nNew content about outreach.", encoding="utf-8")
    _, s3 = build_engine(config, embedder=embedder, llm=fake_llm)
    assert s3.index_state.startswith("rebuilt")
