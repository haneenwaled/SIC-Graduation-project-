"""Retail AI Intelligence Portal - enhanced Streamlit frontend.

Same backend contract as before:
  GET  {API}/recommendations/{customer_id}  -> {"recommendations": [...]}
  POST {API}/predict-lapse                  -> {"lapse_probability": float, "risk_category": str}
  POST {API}/rag-chat   {"question": str}   -> {"answer": str, (optional) "sources"/"citations": [...]}
Run:  streamlit run app_streamlit.py
"""
import os

import pandas as pd
import requests
import streamlit as st

DEFAULT_API = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = 30
RISK_MEDIUM, RISK_HIGH = 0.30, 0.50  # cut points from business_rules_kpis.md 9.1

COUNTRIES = ["United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands", "Belgium",
             "Switzerland", "Portugal", "Australia", "Norway", "Italy", "Other"]

PRESETS = {
    "Loyal customer": dict(recency=12, freq=24, monetary=3200.0, aov=133.0, abq=18.0, distinct_p=60,
                           tenure=700, avg_days=25.0, o_30d=2, o_90d=4, o_180d=8,
                           s_30d=260.0, s_90d=540.0, s_180d=1050.0, canc_cnt=0, canc_val=0.0, canc_rate=0.0),
    "At-risk customer": dict(recency=120, freq=5, monetary=450.0, aov=90.0, abq=12.5, distinct_p=15,
                             tenure=365, avg_days=30.0, o_30d=0, o_90d=0, o_180d=2,
                             s_30d=0.0, s_90d=0.0, s_180d=150.0, canc_cnt=0, canc_val=0.0, canc_rate=0.0),
    "Dormant + cancellations": dict(recency=260, freq=3, monetary=210.0, aov=70.0, abq=8.0, distinct_p=7,
                                    tenure=420, avg_days=75.0, o_30d=0, o_90d=0, o_180d=0,
                                    s_30d=0.0, s_90d=0.0, s_180d=0.0, canc_cnt=2, canc_val=64.0, canc_rate=0.4),
}

RAG_EXAMPLES = [
    "What retention actions do you recommend for high-risk customers?",
    "How is risk_category derived from lapse_probability?",
    "What are the promotion eligibility rules?",
    "Which KPIs does the business track?",
]

st.set_page_config(page_title="Retail AI Portal", page_icon="🛒", layout="wide",
                   initial_sidebar_state="expanded")

# ------------------------------------------------------------------ styling
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1250px;}
.hero {background: linear-gradient(120deg,#4f46e5 0%,#7c3aed 55%,#db2777 100%);
       padding: 1.4rem 1.8rem; border-radius: 16px; color: #fff; margin-bottom: 1.2rem;}
.hero h1 {margin: 0; font-size: 1.9rem; color: #fff;}
.hero p {margin: .3rem 0 0; opacity: .9;}
div[data-testid="stMetric"] {background: rgba(124,58,237,.07); border: 1px solid rgba(124,58,237,.18);
       padding: .8rem 1rem; border-radius: 12px;}
.risk-card {padding: 1.3rem 1.5rem; border-radius: 14px; color: #fff; margin: .6rem 0 1rem;}
.risk-High {background: linear-gradient(120deg,#dc2626,#f97316);}
.risk-Medium {background: linear-gradient(120deg,#d97706,#facc15); color:#1f1f1f;}
.risk-Low {background: linear-gradient(120deg,#059669,#34d399);}
.risk-card h2 {margin: 0; font-size: 1.6rem; color: inherit;}
.risk-card p {margin: .2rem 0 0; opacity: .92;}
.bar {position: relative; height: 16px; border-radius: 8px; margin: .6rem 0 .2rem;
      background: linear-gradient(90deg,#34d399 0%,#34d399 30%,#facc15 30%,#facc15 50%,#f97316 50%,#dc2626 100%);}
.marker {position: absolute; top: -6px; width: 4px; height: 28px; background: #111; border-radius: 2px;
         box-shadow: 0 0 0 2px #fff;}
.bar-labels {display: flex; justify-content: space-between; font-size: .75rem; opacity: .7;}
.src-pill {display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:999px;
           background: rgba(124,58,237,.12); font-size:.78rem;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def api_url() -> str:
    return st.session_state.get("api_base", DEFAULT_API).rstrip("/")


def risk_from_probability(p: float) -> str:
    return "High" if p >= RISK_HIGH else "Medium" if p >= RISK_MEDIUM else "Low"


@st.cache_data(ttl=60, show_spinner=False)
def fetch_recommendations(base: str, cid: int):
    r = requests.get(f"{base}/recommendations/{cid}", timeout=TIMEOUT)
    if r.status_code == 200:
        return r.status_code, r.json().get("recommendations", [])
    return r.status_code, None


@st.cache_data(ttl=15, show_spinner=False)
def check_health(base: str) -> bool:
    root = base.rsplit("/api", 1)[0]
    for url in (f"{root}/health", f"{root}/docs", base):
        try:
            if requests.get(url, timeout=3).status_code < 500:
                return True
        except requests.RequestException:
            continue
    return False


def apply_preset(name: str) -> None:
    for k, v in PRESETS[name].items():
        st.session_state[f"lp_{k}"] = v


def init_state() -> None:
    st.session_state.setdefault("api_base", DEFAULT_API)
    st.session_state.setdefault("chat", [])
    st.session_state.setdefault("pending_q", None)
    st.session_state.setdefault("lapse_history", [])
    for k, v in PRESETS["At-risk customer"].items():
        st.session_state.setdefault(f"lp_{k}", v)


init_state()

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.text_input("API base URL", key="api_base")
    online = check_health(api_url())
    st.markdown(f"**Backend:** {'🟢 online' if online else '🔴 unreachable'}")
    if st.button("Re-check connection", use_container_width=True):
        check_health.clear()
        st.rerun()
    st.divider()
    st.markdown("### Risk categories")
    st.markdown(f"🟢 **Low** &lt; {RISK_MEDIUM:.2f}  \n🟠 **Medium** {RISK_MEDIUM:.2f} – {RISK_HIGH:.2f}  \n"
                f"🔴 **High** ≥ {RISK_HIGH:.2f}", unsafe_allow_html=True)
    st.caption("Lapse = no purchase in the following 90 days. Probabilities are model estimates; "
               "calibration is unverified.")
    st.divider()
    st.caption("Offers and outreach require human approval before being sent.")

# ------------------------------------------------------------------ header
st.markdown("""
<div class="hero"><h1>🛒 Retail AI Intelligence Portal</h1>
<p>Product recommendations · customer lapse risk · policy &amp; retention assistant</p></div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💡 Customer Recommendations", "🚨 Lapse Risk Prediction", "💬 Retail RAG Assistant"])

# ================================================================== TAB 1
with tab1:
    st.subheader("Product Recommendations Lookup")
    c1, c2 = st.columns([3, 1])
    with c1:
        customer_id = st.number_input("Customer ID", min_value=1, value=12346, step=1, key="rec_cid")
    with c2:
        st.write("")
        st.write("")
        go = st.button("Fetch Recommendations", type="primary", use_container_width=True)

    if go:
        with st.spinner("Fetching top recommendations from database..."):
            try:
                status, recs = fetch_recommendations(api_url(), int(customer_id))
                st.session_state["rec_result"] = (int(customer_id), status, recs)
            except requests.RequestException as e:
                st.session_state["rec_result"] = (int(customer_id), -1, str(e))

    if "rec_result" in st.session_state:
        cid, status, recs = st.session_state["rec_result"]
        if status == 200 and recs:
            df = pd.DataFrame(recs)
            if "rank" in df:
                df = df.sort_values("rank")
            st.success(f"Top {len(df)} recommendations for Customer #{cid}")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Products", len(df))
            if "estimated_basket_value_gbp" in df:
                m2.metric("Est. basket value", f"£{df['estimated_basket_value_gbp'].sum():,.2f}")
                m3.metric("Avg per product", f"£{df['estimated_basket_value_gbp'].mean():,.2f}")
            if "recommendation_score" in df:
                m4.metric("Top score", f"{df['recommendation_score'].max():.3f}")

            left, right = st.columns([3, 2])
            with left:
                cfg = {
                    "rank": st.column_config.NumberColumn("Rank", width="small"),
                    "stock_code": st.column_config.TextColumn("SKU", width="small"),
                    "product_name": st.column_config.TextColumn("Product", width="large"),
                    "recommendation_score": st.column_config.ProgressColumn(
                        "Score", min_value=0.0, max_value=float(max(1.0, df.get("recommendation_score", pd.Series([1])).max())),
                        format="%.3f"),
                    "median_unit_price": st.column_config.NumberColumn("Unit price", format="£%.2f"),
                    "median_quantity": st.column_config.NumberColumn("Qty", format="%.0f"),
                    "estimated_basket_value_gbp": st.column_config.NumberColumn("Est. value", format="£%.2f"),
                }
                hide = [c for c in ("customer_id",) if c in df]
                st.dataframe(df.drop(columns=hide), column_config=cfg, hide_index=True, use_container_width=True)
            with right:
                if {"product_name", "recommendation_score"} <= set(df.columns):
                    st.markdown("**Recommendation score**")
                    chart = df.set_index("product_name")["recommendation_score"]
                    st.bar_chart(chart, horizontal=True, height=360)

            st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name=f"recommendations_{cid}.csv", mime="text/csv")
            st.caption("Score is a ranking signal, not a calibrated purchase probability. Estimated value = median "
                       "unit price × median quantity (historical proxy, not expected revenue).")
        elif status == 200:
            st.info(f"No recommendations returned for Customer #{cid}.")
        elif status == 404:
            st.warning(f"No recommendations found for Customer #{cid}")
        elif status == -1:
            st.error(f"Failed to connect to backend: {recs}")
        else:
            st.error(f"API Error: {status}")

# ================================================================== TAB 2
with tab2:
    st.subheader("Customer Churn Risk Inference")
    st.caption("Load a preset profile or enter customer features manually.")
    pc = st.columns(len(PRESETS))
    for col, name in zip(pc, PRESETS):
        col.button(name, on_click=apply_preset, args=(name,), use_container_width=True, key=f"preset_{name}")

    with st.form("lapse_form"):
        c_id = st.number_input("Customer ID", min_value=1, value=12346, step=1)
        a, b, c = st.columns(3)
        with a:
            st.markdown("**Value & behaviour**")
            recency = st.number_input("Recency (Days)", min_value=0, key="lp_recency")
            freq = st.number_input("Frequency (Orders)", min_value=0, key="lp_freq")
            monetary = st.number_input("Monetary (Total Spend GBP)", min_value=0.0, key="lp_monetary")
            aov = st.number_input("Average Order Value", min_value=0.0, key="lp_aov")
            abq = st.number_input("Average Basket Quantity", min_value=0.0, key="lp_abq")
            distinct_p = st.number_input("Distinct Products", min_value=0, key="lp_distinct_p")
        with b:
            st.markdown("**Timing & recent activity**")
            tenure = st.number_input("Tenure (Days)", min_value=0, key="lp_tenure")
            avg_days = st.number_input("Avg Days Between Orders", min_value=0.0, key="lp_avg_days")
            o_30d = st.number_input("Orders (Last 30d)", min_value=0, key="lp_o_30d")
            o_90d = st.number_input("Orders (Last 90d)", min_value=0, key="lp_o_90d")
            o_180d = st.number_input("Orders (Last 180d)", min_value=0, key="lp_o_180d")
        with c:
            st.markdown("**Spend & cancellations**")
            s_30d = st.number_input("Spend (Last 30d)", min_value=0.0, key="lp_s_30d")
            s_90d = st.number_input("Spend (Last 90d)", min_value=0.0, key="lp_s_90d")
            s_180d = st.number_input("Spend (Last 180d)", min_value=0.0, key="lp_s_180d")
            canc_cnt = st.number_input("Cancellation Count", min_value=0, key="lp_canc_cnt")
            canc_val = st.number_input("Cancellation Value", min_value=0.0, key="lp_canc_val")
            canc_rate = st.number_input("Cancellation Rate", min_value=0.0, max_value=1.0, key="lp_canc_rate")
            country = st.selectbox("Country", COUNTRIES)
        submitted = st.form_submit_button("Predict Lapse Risk", type="primary", use_container_width=True)

    if submitted:
        problems = []
        if not (o_30d <= o_90d <= o_180d):
            problems.append("Order counts should be cumulative: 30d ≤ 90d ≤ 180d.")
        if not (s_30d <= s_90d <= s_180d):
            problems.append("Spend should be cumulative: 30d ≤ 90d ≤ 180d.")
        for p in problems:
            st.warning(p)

        payload = {
            "customer_id": int(c_id), "recency_days": recency, "frequency_orders": freq,
            "monetary": monetary, "average_order_value": aov, "average_basket_quantity": abq,
            "distinct_products": distinct_p, "tenure_days": tenure,
            "average_days_between_orders": avg_days, "orders_last_30d": o_30d,
            "orders_last_90d": o_90d, "orders_last_180d": o_180d, "spend_last_30d": s_30d,
            "spend_last_90d": s_90d, "spend_last_180d": s_180d, "cancellation_count": canc_cnt,
            "cancellation_value": canc_val, "cancellation_rate": canc_rate, "country": country,
        }
        with st.spinner("Scoring customer..."):
            try:
                res = requests.post(f"{api_url()}/predict-lapse", json=payload, timeout=TIMEOUT)
                if res.status_code == 200:
                    r = res.json()
                    st.session_state["lapse_result"] = (int(c_id), r["lapse_probability"], r["risk_category"])
                    st.session_state["lapse_history"].insert(
                        0, {"Customer": int(c_id), "Probability %": round(r["lapse_probability"] * 100, 2),
                            "Category": r["risk_category"], "Recency": recency, "Orders": freq,
                            "Spend £": monetary})
                    st.session_state["lapse_history"] = st.session_state["lapse_history"][:10]
                else:
                    try:
                        detail = res.json().get("detail", "Prediction failed")
                    except ValueError:
                        detail = "Prediction failed"
                    st.error(f"Error: {detail}")
            except requests.RequestException as e:
                st.error(f"Connection error: {e}")

    if "lapse_result" in st.session_state:
        cid, prob, cat = st.session_state["lapse_result"]
        icon = {"High": "⚠️", "Medium": "⚡", "Low": "✅"}.get(cat, "ℹ️")
        st.markdown(
            f'<div class="risk-card risk-{cat}"><h2>{icon} Churn Risk: {cat}</h2>'
            f'<p>Customer #{cid} · estimated lapse probability <b>{prob * 100:.2f}%</b> '
            f'(no purchase in next 90 days)</p></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="bar"><div class="marker" style="left:calc({min(prob, 1) * 100:.1f}% - 2px)"></div></div>'
            f'<div class="bar-labels"><span>0%</span><span>30%</span><span>50%</span><span>100%</span></div>',
            unsafe_allow_html=True)
        if cat == "High":
            st.info("Suggested next step: review in the retention workflow. Any offer needs human approval.")

    if st.session_state["lapse_history"]:
        with st.expander("Recent predictions (this session)"):
            st.dataframe(pd.DataFrame(st.session_state["lapse_history"]), hide_index=True,
                         use_container_width=True)
            if st.button("Clear history"):
                st.session_state["lapse_history"] = []
                st.rerun()

# ================================================================== TAB 3
with tab3:
    st.subheader("Product & Customer Intelligence Assistant")
    top = st.columns([6, 1])
    top[0].caption("Answers are grounded in the retention playbook, promotion policy, business rules and product catalog.")
    if top[1].button("🗑️ Clear", use_container_width=True):
        st.session_state["chat"] = []
        st.rerun()

    if not st.session_state["chat"]:
        st.markdown("**Try asking:**")
        ex_cols = st.columns(2)
        for i, q in enumerate(RAG_EXAMPLES):
            if ex_cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
                st.session_state["pending_q"] = q
                st.rerun()

    for msg in st.session_state["chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.markdown("".join(f'<span class="src-pill">{s}</span>' for s in msg["sources"]),
                            unsafe_allow_html=True)

    typed = st.chat_input("Ask about product recommendations, policies or customer segments...")
    question = typed or st.session_state.pop("pending_q", None)

    if question:
        st.session_state["chat"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving context..."):
                try:
                    res = requests.post(f"{api_url()}/rag-chat", json={"question": question}, timeout=90)
                    if res.status_code == 200:
                        data = res.json()
                        answer = data.get("answer", "")
                        raw = data.get("sources") or data.get("citations") or []
                        sources = [s if isinstance(s, str) else
                                   " · ".join(str(s[k]) for k in ("label", "source", "section") if s.get(k))
                                   for s in raw]
                        st.markdown(answer)
                        if sources:
                            st.markdown("".join(f'<span class="src-pill">{s}</span>' for s in sources),
                                        unsafe_allow_html=True)
                        st.session_state["chat"].append({"role": "assistant", "content": answer, "sources": sources})
                    else:
                        err = "RAG Service unavailable."
                        st.error(err)
                        st.session_state["chat"].append({"role": "assistant", "content": f"⚠️ {err}"})
                except requests.RequestException as e:
                    err = f"Error: {e}"
                    st.error(err)
                    st.session_state["chat"].append({"role": "assistant", "content": f"⚠️ {err}"})