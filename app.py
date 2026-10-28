"""Retain & Recommend AI - Streamlit application (assistant chat + manager dashboard)."""
from __future__ import annotations

import inspect

import altair as alt
import pandas as pd
import streamlit as st

from src.config import RISK_ORDER, Config
from src.customer_data import PROBABILITY_VS_CATEGORY, CustomerDataError, format_table
from src.document_loader import MissingFilesError
from src.llm_client import SETUP_HELP
from src.query_router import detect_language
from src.rag_engine import Answer, build_engine

st.set_page_config(page_title="Retain & Recommend AI", page_icon="🎯", layout="wide")

EXAMPLES = [
    "Summarize customer lapse risk in the latest snapshot.",
    "Which customers have the highest lapse probabilities?",
    "Explain the risk categories used in this project.",
    "What retention actions does the playbook suggest for high-risk customers?",
    "Explain the promotion approval rules.",
    "Find products matching wrapping tape in the catalog.",
    "What data is missing before we can estimate customer value?",
    "Explain the KPIs documented in the business rules.",
    "Show the evidence behind your recommendation.",
    "Which customers have the highest lapse risk in the latest snapshot, and what retention actions should we consider?",
]


def stretch(fn) -> dict:
    """Full-width kwarg that works on both older (use_container_width) and newer (width) Streamlit."""
    return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}


AR_EXAMPLES = [
    "لخص مخاطر انقطاع العملاء في آخر لقطة.",
    "أي العملاء لديهم أعلى احتمال للانقطاع؟",
    "اشرح فئات المخاطر المستخدمة في هذا المشروع.",
    "ما الإجراءات التي يقترحها دليل الاحتفاظ للعملاء عالي الخطر؟",
    "اشرح قواعد الموافقة على العروض الترويجية.",
    "ما البيانات الناقصة لتقدير قيمة العميل؟",
    "اشرح مؤشرات الأداء الموجودة في القواعد التجارية.",
    "أي العملاء الأعلى خطرا في آخر لقطة، وما الإجراءات التي نفكر فيها؟",
    "اعرض الأدلة وراء توصيتك.",
]
RISK_COLORS = {"Low": "#2e9e6b", "Medium": "#e0a030", "High": "#d9534f"}

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {padding: 1rem 1.25rem; border-radius: 12px; background: linear-gradient(90deg,#1f3a5f,#2d6a8f); color: #fff; margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 1.7rem; color: #fff;} .hero p {margin: .25rem 0 0; opacity: .92;}
.rtl {direction: rtl; text-align: right;}
.small-note {font-size: .82rem; opacity: .75;}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- engine loading
@st.cache_resource(show_spinner="Loading documents and building the search index (first run can take a few minutes)...")
def load_engine():
    config = Config.from_env()
    try:
        engine, status = build_engine(config)
        return {"config": config, "engine": engine, "status": status, "error": None}
    except MissingFilesError as exc:
        return {"config": config, "error": f"{exc}\n\nCopy the missing file(s) into the `data/` folder and restart."}
    except CustomerDataError as exc:
        return {"config": config, "error": str(exc)}
    except Exception as exc:  # keep the UI alive and show a useful message
        return {"config": config, "error": f"Startup failed: {type(exc).__name__}: {exc}"}


boot = load_engine()
config: Config = boot["config"]
engine = boot.get("engine")
status = boot.get("status")

st.session_state.setdefault("messages", [])
st.session_state.setdefault("history", [])
st.session_state.setdefault("last_answer", None)


# ---------------------------------------------------------------- helpers
def render_evidence(ans: Answer) -> None:
    if not (ans.tables or ans.citations or ans.warnings or ans.route):
        return
    with st.expander("📎 Evidence and sources", expanded=False):
        if ans.route:
            parts = []
            if ans.route.needs_customer_data:
                parts.append(f"structured customer data (snapshot **{ans.snapshot}**)")
            if ans.route.needs_knowledge:
                parts.append("policy / playbook / KPI documents")
            if ans.route.needs_catalog:
                parts.append("product catalog")
            if parts:
                st.caption("How this was answered: " + " + ".join(parts) + ". Numbers come from Python/Pandas, not from the LLM.")
        for title, df in ans.tables:
            st.markdown(f"**{title}**  \n<span class='small-note'>Fields: customer_id, snapshot_date, lapse_probability, risk_category</span>"
                        if "Customer" in title or "customers" in title else f"**{title}**", unsafe_allow_html=True)
            st.dataframe(df, hide_index=True, **stretch(st.dataframe))
        if ans.citations:
            st.markdown("**Document passages supplied to the model**")
            for cit, rc in zip(ans.citations, ans.chunks):
                st.markdown(f"**[{cit['label']}] `{cit['source']}`** — {cit['section'].split(' > ')[-1]}  "
                            f"<span class='small-note'>({cit['doc_type']}, similarity {cit['score']})</span>", unsafe_allow_html=True)
                with st.expander("Show passage"):
                    st.text(rc.chunk.text[:1500])
        for w in ans.warnings:
            st.warning(w)


def show_text(text: str, language: str) -> None:
    """Render Markdown; Arabic text is shown right-to-left."""
    if language == "ar":
        st.markdown(f"<div class='rtl' dir='rtl'>\n\n{text}\n\n</div>", unsafe_allow_html=True)
    else:
        st.markdown(text)



def render_answer(ans: Answer) -> None:
    if ans.error:
        st.error(ans.error)

    # Display the generated explanation.
    show_text(ans.text, ans.language)

    # Display computed tables directly from Python/Pandas.
    if ans.tables:
        st.markdown("### 📊 Actual data results")

        for title, df in ans.tables:
            st.markdown(f"**{title}**")

            if df.empty:
                st.info("No matching records were found in the selected snapshot.")
            else:
                st.dataframe(
                    df,
                    hide_index=True,
                    **stretch(st.dataframe),
                )

    # Keep source documents, citations, and warnings available.
    render_evidence(ans)



def ask(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        show_text(question, detect_language(question))
    with st.chat_message("assistant"):
        with st.spinner("Retrieving evidence and generating the answer... / جارٍ استرجاع الأدلة وتوليد الإجابة..."):
            ans = engine.answer(question, st.session_state.history, st.session_state.last_answer)
        render_answer(ans)
    st.session_state.messages.append({"role": "assistant", "content": ans.text, "answer": ans})
    if ans.route and ans.route.intent != "evidence" and (ans.used_llm or ans.tables or ans.citations):
        st.session_state.last_answer = ans
    if ans.used_llm:
        st.session_state.history.append((question, ans.text))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("🎯 Retain & Recommend AI")
    st.subheader("System status")
    if config.api_key_configured:
        st.success(f"Gemini key configured · model `{config.gemini_model}`")
    else:
        st.warning("Gemini API key missing. Data and evidence still work; written answers need a key.")
        with st.expander("How to set it up"):
            st.markdown(SETUP_HELP)
    if status:
        if status.embedder_fallback:
            st.warning("Embedding model not loaded: using a low-quality offline fallback. See README → Troubleshooting.")
        else:
            st.success(f"Embeddings: `{status.embedder_name}`")
        st.caption(f"Index {status.index_state} · {status.n_chunks:,} chunks")
        for w in status.warnings:
            if "embedding model" not in w:
                st.warning(w)
        st.subheader("Data")
        cd = engine.customers
        st.write(f"**{cd.total_customers():,}** distinct customers · snapshot **{cd.latest_snapshot():%Y-%m-%d}** "
                 f"({len(cd.snapshots())} snapshot{'s' if len(cd.snapshots()) != 1 else ''})")
        st.caption("Chunks: " + ", ".join(f"{k.replace('_', ' ')} {v:,}" for k, v in status.chunk_counts.items()))
        if cd.report.issues:
            st.warning("Customer file quality issues: " + "; ".join(cd.report.issues))
        else:
            st.caption("Customer file passed all validation checks.")
        st.subheader("Example questions")
        for i, ex in enumerate(EXAMPLES):
            if st.button(ex, key=f"side_ex_{i}", **stretch(st.button)):
                st.session_state["pending"] = ex
        with st.expander("أسئلة بالعربي (Arabic examples)"):
            for i, ex in enumerate(AR_EXAMPLES):
                if st.button(ex, key=f"side_ar_{i}", **stretch(st.button)):
                    st.session_state["pending"] = ex
        if st.button("🗑️ Clear conversation", **stretch(st.button)):
            st.session_state.update(messages=[], history=[], last_answer=None)
            st.rerun()
    st.divider()
    st.caption("🔒 Privacy: your files stay on this computer. Only your question, computed data results and the "
               "retrieved passages are sent to the Gemini API when an answer is generated.")

# ---------------------------------------------------------------- setup error
st.markdown("<div class='hero'><h1>Retain &amp; Recommend AI</h1>"
            "<p>Returns-aware product recommendation, customer lapse prediction and a RAG-powered retention assistant.</p></div>",
            unsafe_allow_html=True)
if boot["error"]:
    st.error("The application could not load its data.")
    st.markdown(boot["error"])
    st.stop()

view = st.radio("View", ["💬 Assistant", "📊 Dashboard"], horizontal=True, label_visibility="collapsed")

# ---------------------------------------------------------------- assistant view
if view == "💬 Assistant":
    if not config.api_key_configured:
        st.info("**Setup needed for written answers:** " + SETUP_HELP + " You can still use the dashboard and see retrieved evidence.")
    if not st.session_state.messages:
        st.markdown("You can ask in **English or Arabic** (يمكنك السؤال بالعربية أو الإنجليزية). Ask about customer lapse risk, retention actions, promotion rules, KPIs or catalog products. "
                    "Every answer lists the evidence it used.")
        with st.expander("🧪 Demonstration panel — click a question to run it", expanded=True):
            cols = st.columns(2)
            for i, ex in enumerate(EXAMPLES):
                if cols[i % 2].button(ex, key=f"demo_ex_{i}", **stretch(st.button)):
                    st.session_state["pending"] = ex
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                render_answer(m["answer"])
            else:
                show_text(m["content"], detect_language(m["content"]))
    question = st.session_state.pop("pending", None) or st.chat_input("Ask in English or Arabic / اسأل بالعربية أو الإنجليزية...")
    if question:
        ask(question)

# ---------------------------------------------------------------- dashboard view
else:
    cd = engine.customers
    snaps = cd.snapshots()
    snap = st.selectbox("Snapshot date", snaps, index=len(snaps) - 1, format_func=lambda s: f"{s:%Y-%m-%d}")
    counts = cd.counts_by_category(snap)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distinct customers", f"{cd.total_customers(snap):,}", help="Unique customer_id values in this snapshot")
    for col, risk in zip((c2, c3, c4), RISK_ORDER):
        row = counts[counts["risk_category"] == risk].iloc[0]
        col.metric(f"{risk} risk", f"{int(row['customers']):,}", f"{row['percent']}% of customers", delta_color="off")
    st.caption(f"CSV rows in this snapshot: {cd.total_rows(snap):,}. Counts are distinct customers, not rows. "
               "Only the four columns in the scoring file are available: no revenue, profit, value tier or purchase history.")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Risk category distribution**")
        chart = alt.Chart(counts).mark_bar().encode(
            x=alt.X("risk_category:N", sort=RISK_ORDER, title=None),
            y=alt.Y("customers:Q", title="Distinct customers"),
            color=alt.Color("risk_category:N", scale=alt.Scale(domain=RISK_ORDER, range=[RISK_COLORS[r] for r in RISK_ORDER]), legend=None),
            tooltip=["risk_category", "customers", "percent"])
        st.altair_chart(chart, **stretch(st.altair_chart))
    with right:
        st.markdown("**Customer detail**")
        cid_text = st.text_input("Customer ID search", placeholder="e.g. 12346")
        if cid_text.strip():
            if not cid_text.strip().isdigit():
                st.error("Please enter a numeric customer ID.")
            else:
                rec = cd.get_customer(int(cid_text))
                if rec.empty:
                    st.warning(f"Customer {cid_text} is not in the scoring file.")
                else:
                    latest = rec[rec["snapshot_date"] == snap]
                    row = latest.iloc[0] if not latest.empty else rec.iloc[0]
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Lapse probability", f"{row['lapse_probability']:.4f}")
                    m2.metric("Risk category", str(row["risk_category"]))
                    pct = cd.urgency_percentile(int(cid_text), row["snapshot_date"])
                    m3.metric("Urgency percentile", f"{pct}" if pct is not None else "n/a", help="Relative rank within the snapshot; not an absolute probability")
                    st.dataframe(format_table(rec), hide_index=True, **stretch(st.dataframe))
                    st.caption("Not available in the file: name, purchases, revenue, cancellations, value tier, flags.")
        else:
            st.caption("Enter a customer ID to see the available risk fields.")

    st.markdown("**Customer table**")
    f1, f2, f3 = st.columns([2, 2, 1])
    cats = f1.multiselect("Risk category", RISK_ORDER, default=RISK_ORDER)
    lo, hi = f2.slider("Lapse probability range", 0.0, 1.0, (0.0, 1.0), 0.01)
    desc = f3.toggle("Highest first", value=True)
    tbl = cd.sort_by_probability(snap, ascending=not desc)
    tbl = tbl[tbl["risk_category"].astype(str).isin(cats) & tbl["lapse_probability"].between(lo, hi)]
    st.caption(f"{len(tbl):,} customers match the filters.")
    st.dataframe(format_table(tbl), hide_index=True, **stretch(st.dataframe), height=360,
                 column_config={"lapse_probability": st.column_config.ProgressColumn("lapse_probability", min_value=0.0, max_value=1.0, format="%.4f")})
    with st.expander("ℹ️ Probability vs. risk category"):
        st.markdown(PROBABILITY_VS_CATEGORY)
    with st.expander("🧪 Data quality report"):
        r = cd.report
        st.write(f"Rows in file: {r.rows_in_file:,} · valid rows used: {r.rows_valid:,} · invalid: {r.invalid_rows} · duplicates: {r.duplicate_rows} · tier conflicts: {r.tier_mismatch_rows}")
        st.write("No issues found." if r.ok else r.issues)
