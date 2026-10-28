"""Orchestrates routing, deterministic customer queries, retrieval, prompting and generation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .chunking import chunk_documents
from .config import CATALOG_FILE, CUSTOMER_FILE, MARKDOWN_FILES, Config
from .customer_data import PROBABILITY_VS_CATEGORY, CustomerData, format_table
from .document_loader import load_all_documents
from .embeddings import Embedder, get_embedder
from .llm_client import GeminiClient, LLMError
from .prompt_builder import SYSTEM_PROMPT, DataResult, build_citation_list, build_user_prompt
from .query_router import Route, extract_product_id, normalize_text, route_question
from .retriever import RetrievedChunk, Retriever
from .vector_store import VectorStore, compute_fingerprint

NO_EVIDENCE_MESSAGE = (
    "I could not find passages in the supplied documents that are relevant enough to answer this reliably, "
    "so I will not guess. Try rephrasing, or check whether this information is covered by the five input files. "
    "If it is not documented there, it should be treated as a data gap."
)


MESSAGES = {
    "en": {
        "no_evidence": NO_EVIDENCE_MESSAGE,
        "llm_failed": "I could not generate a written answer, but the data and sources retrieved for your question are shown below.",
        "no_prev": "There is no previous answer with evidence to show yet. Ask a question first.",
        "evidence_intro": "Here is the evidence that was supplied for my previous answer (shown below). Only sources listed there were given to the model.",
    },
    "ar": {
        "no_evidence": "لم أجد في المستندات المرفقة فقرات ذات صلة كافية للإجابة بشكل موثوق، لذلك لن أخمّن. حاول إعادة صياغة السؤال، أو تحقق مما إذا كانت هذه المعلومة مغطاة في ملفات الإدخال الخمسة. إذا لم تكن موثقة فيها فهي فجوة في البيانات.",
        "llm_failed": "تعذّر توليد إجابة مكتوبة، لكن البيانات والمصادر التي تم استرجاعها لسؤالك معروضة أدناه.",
        "no_prev": "لا توجد إجابة سابقة بأدلة لعرضها بعد. اطرح سؤالاً أولاً.",
        "evidence_intro": "هذه هي الأدلة التي قُدّمت لإجابتي السابقة (معروضة أدناه). المصادر المدرجة فقط هي التي أُعطيت للنموذج.",
    },
}


@dataclass
class Answer:
    text: str
    route: Route | None = None
    citations: list[dict] = field(default_factory=list)
    chunks: list[RetrievedChunk] = field(default_factory=list)
    tables: list[tuple[str, pd.DataFrame]] = field(default_factory=list)
    snapshot: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    used_llm: bool = False
    data_summary: list[str] = field(default_factory=list)
    language: str = "en"


def df_to_markdown(df: pd.DataFrame) -> str:
    """Dependency-free Markdown table."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


class RagEngine:
    def __init__(self, customers: CustomerData, retriever: Retriever, llm: GeminiClient,
                 load_warnings: list[str] | None = None):
        self.customers = customers
        self.retriever = retriever
        self.llm = llm
        self.load_warnings = load_warnings or []

    # ---- deterministic customer operations ---------------------------------
    def run_customer_ops(self, route: Route) -> tuple[list[DataResult], list[tuple[str, pd.DataFrame]], str, list[str]]:
        cd = self.customers
        warnings: list[str] = []
        snap = cd.latest_snapshot()
        if route.snapshot_date:
            try:
                req = pd.Timestamp(route.snapshot_date)
                if req in cd.snapshots():
                    snap = req
                else:
                    avail = ", ".join(s.strftime("%Y-%m-%d") for s in cd.snapshots())
                    warnings.append(f"Snapshot {route.snapshot_date} does not exist; used the latest ({snap:%Y-%m-%d}). Available: {avail}.")
            except ValueError:
                warnings.append(f"Could not read snapshot date '{route.snapshot_date}'; used the latest.")
        snap_s = f"{snap:%Y-%m-%d}"
        results: list[DataResult] = []
        tables: list[tuple[str, pd.DataFrame]] = []

        def add(title: str, text: str, table: pd.DataFrame | None = None) -> None:
            results.append(DataResult(f"D{len(results) + 1}", title, text))
            if table is not None:
                tables.append((title, format_table(table)))

        ops = route.customer_ops or [{"op": "summary"}]
        for op in ops:
            kind = op["op"]
            if kind == "summary":
                counts = cd.counts_by_category(snap)
                stats = cd.probability_stats(snap)
                text = (f"Source: {CUSTOMER_FILE}, snapshot {snap_s}. Distinct customers: {cd.total_customers(snap)} "
                        f"(CSV rows in this snapshot: {cd.total_rows(snap)}).\n{df_to_markdown(counts)}\n"
                        f"lapse_probability: min {stats['min']:.4f}, median {stats['median']:.4f}, "
                        f"mean {stats['mean']:.4f}, max {stats['max']:.4f}.")
                add(f"Risk category counts (snapshot {snap_s})", text, counts)
            elif kind == "top":
                n, cat, asc = op.get("n", 10), op.get("category"), op.get("ascending", False)
                top = cd.sort_by_probability(snap, ascending=asc, n=n, category=cat)
                scope = f"{cat}-risk customers" if cat else "customers"
                title = f"{'Lowest' if asc else 'Highest'} {len(top)} {scope} by lapse_probability (snapshot {snap_s})"
                if top.empty:
                    add(title, "No matching customers in this snapshot.")
                else:
                    shown = format_table(top)
                    add(title, f"Source: {CUSTOMER_FILE}. Sorted by lapse_probability, ties by customer_id.\n{df_to_markdown(shown)}", top)
            elif kind == "lookup":
                cid = op["customer_id"]
                rec = cd.get_customer(cid)
                if rec.empty:
                    warnings.append(f"Customer {cid} was not found in {CUSTOMER_FILE}.")
                    add(f"Customer {cid}", f"Customer {cid} does not appear in {CUSTOMER_FILE}. No other data exists for this customer.")
                else:
                    pct = cd.urgency_percentile(cid, snap)
                    pct_txt = f" Urgency percentile in snapshot {snap_s}: {pct} (relative rank only)." if pct is not None else ""
                    add(f"Customer {cid} records", f"Source: {CUSTOMER_FILE}.\n{df_to_markdown(format_table(rec))}\n{pct_txt}", rec)
            elif kind == "explain_categories":
                add("Probability vs. risk category", PROBABILITY_VS_CATEGORY)
        issues = cd.report.issues
        if issues:
            warnings.append("Data quality issues in the customer file: " + "; ".join(issues))
        return results, tables, snap_s, warnings

    # ---- main entry point ----------------------------------------------------
    def answer(self, question: str, history: list[tuple[str, str]] | None = None,
               last_answer: Answer | None = None) -> Answer:
        route = route_question(question)
        msg = MESSAGES[route.language]

        if route.intent == "evidence":
            if last_answer is None or (not last_answer.citations and not last_answer.tables):
                return Answer(msg["no_prev"], route, language=route.language)
            return Answer(msg["evidence_intro"], route, language=route.language,
                          citations=last_answer.citations, chunks=last_answer.chunks,
                          tables=last_answer.tables, snapshot=last_answer.snapshot)

        data_results: list[DataResult] = []
        tables: list[tuple[str, pd.DataFrame]] = []
        snapshot: str | None = None
        warnings: list[str] = []
        if route.needs_customer_data:
            data_results, tables, snapshot, warnings = self.run_customer_ops(route)

        if route.intent == "policy" and re.search(r"categor|probabilit|فئ|احتمال", normalize_text(question), re.I):
            data_results.append(DataResult(f"D{len(data_results) + 1}", "Probability vs. risk category", PROBABILITY_VS_CATEGORY))

        chunks: list[RetrievedChunk] = []
        if route.needs_knowledge:
            chunks += self.retriever.retrieve_knowledge(route.retrieval_query or question, route.doc_types)
            if route.intent == "mixed":  # make sure segment-specific action guidance is not crowded out
                cats = [o.get("category") for o in route.customer_ops if o.get("category")]
                tier = cats[0] if cats else "High"
                extra = self.retriever.retrieve_knowledge(
                    f"recommended retention actions for {tier} risk customers", ("retention_playbook",), top_k=3)
                seen = {c.chunk.chunk_id for c in chunks}
                chunks += [e for e in extra if e.chunk.chunk_id not in seen]
        if route.needs_catalog:
            pid = extract_product_id(question)
            exact = self.retriever.lookup_product_id(pid) if pid else None
            prods = self.retriever.retrieve_products(route.retrieval_query or question)
            if exact and all(p.chunk.chunk_id != exact.chunk.chunk_id for p in prods):
                prods.insert(0, exact)
            chunks += prods

        notes: list[str] = []
        if route.needs_knowledge and not any(c.chunk.doc_type != "product_catalog" for c in chunks):
            notes.append("No policy/playbook/KPI passage reached the relevance threshold; do not state document-based guidance.")
        if route.needs_catalog and not any(c.chunk.doc_type == "product_catalog" for c in chunks):
            notes.append("No catalog product matched the query.")
        if snapshot:
            notes.append(f"Customer data comes from snapshot {snapshot}; do not describe it as current.")

        ans = Answer("", route, citations=build_citation_list(chunks), chunks=chunks, tables=tables,
                     snapshot=snapshot, warnings=warnings, language=route.language)

        if not data_results and not chunks:
            ans.text = msg["no_evidence"]
            return ans

        prompt = build_user_prompt(question, data_results, chunks, history, notes, route.language)
        try:
            ans.text = self.llm.generate(SYSTEM_PROMPT, prompt)
            ans.used_llm = True
        except LLMError as exc:
            ans.error = str(exc)
            ans.text = msg["llm_failed"]
        return ans


# ---- factory ---------------------------------------------------------------------------------
@dataclass
class EngineStatus:
    n_chunks: int
    embedder_name: str
    embedder_fallback: bool
    index_state: str                 # "loaded from cache" | "rebuilt (sources changed or first run)"
    warnings: list[str]
    chunk_counts: dict[str, int]


def build_engine(config: Config, embedder: Embedder | None = None, llm: GeminiClient | None = None
                 ) -> tuple[RagEngine, EngineStatus]:
    """Load data, build or reuse the cached FAISS index, and assemble the engine."""
    warnings: list[str] = []
    data_dir = Path(config.data_dir)
    report = load_all_documents(data_dir)
    warnings += report.warnings
    customers = CustomerData.from_csv(data_dir / CUSTOMER_FILE)

    emb_warning = None
    if embedder is None:
        embedder, emb_warning = get_embedder(config.embedding_model)
    if emb_warning:
        warnings.append(emb_warning)

    chunks = chunk_documents(report.documents, config.chunk_size, config.chunk_overlap)
    files = [data_dir / n for n in (*MARKDOWN_FILES, CATALOG_FILE)]
    fp = compute_fingerprint(files, config.chunk_size, config.chunk_overlap, embedder.name)
    store = VectorStore.load_if_fresh(config.cache_dir, fp)
    state = "loaded from cache"
    if store is None:
        store = VectorStore.build(chunks, embedder, fp)
        try:
            store.save(config.cache_dir)
        except OSError as exc:
            warnings.append(f"Could not write the index cache ({exc}); it will be rebuilt next start.")
        state = "rebuilt (sources changed or first run)"

    counts: dict[str, int] = {}
    for c in store.chunks:
        counts[c.doc_type] = counts.get(c.doc_type, 0) + 1
    retriever = Retriever(store, embedder, top_k=config.top_k, min_score=config.min_score if not embedder.is_fallback else None)
    engine = RagEngine(customers, retriever, llm or GeminiClient(config), warnings)
    status = EngineStatus(len(store.chunks), embedder.name, embedder.is_fallback, state, warnings, counts)
    return engine, status
