import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Retail AI Dashboard", layout="wide")
st.title("🛒 Retail AI Intelligence Portal")

tab1, tab2, tab3 = st.tabs(["💡 Customer Recommendations", "🚨 Lapse Risk Prediction", "💬 Retail RAG Assistant"])

# ---------------- TAB 1: RECOMMENDATIONS ----------------
with tab1:
    st.header("Product Recommendations Lookup")
    customer_id = st.number_input("Enter Customer ID:", min_value=1, value=12346, step=1)
    
    if st.button("Fetch Recommendations"):
        with st.spinner("Fetching top recommendations from database..."):
            try:
                res = requests.get(f"{API_BASE_URL}/recommendations/{customer_id}")
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"Top 10 Recommendations for Customer #{customer_id}")
                    st.dataframe(data["recommendations"], use_container_width=True)
                elif res.status_code == 404:
                    st.warning(f"No recommendations found for Customer #{customer_id}")
                else:
                    st.error(f"API Error: {res.status_code}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")

# ---------------- TAB 2: LAPSE PREDICTION ----------------
with tab2:
    st.header("Customer Churn Risk Inference")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        c_id = st.number_input("Customer ID", value=12346)
        recency = st.number_input("Recency (Days)", value=120)
        freq = st.number_input("Frequency (Orders)", value=5)
        monetary = st.number_input("Monetary (Total Spend GBP)", value=450.0)
        aov = st.number_input("Average Order Value", value=90.0)
        abq = st.number_input("Average Basket Quantity", value=12.5)
    with col2:
        distinct_p = st.number_input("Distinct Products", value=15)
        tenure = st.number_input("Tenure (Days)", value=365)
        avg_days = st.number_input("Avg Days Between Orders", value=30.0)
        o_30d = st.number_input("Orders (Last 30d)", value=0)
        o_90d = st.number_input("Orders (Last 90d)", value=0)
        o_180d = st.number_input("Orders (Last 180d)", value=2)
    with col3:
        s_30d = st.number_input("Spend (Last 30d)", value=0.0)
        s_90d = st.number_input("Spend (Last 90d)", value=0.0)
        s_180d = st.number_input("Spend (Last 180d)", value=150.0)
        canc_cnt = st.number_input("Cancellation Count", value=0)
        canc_val = st.number_input("Cancellation Value", value=0.0)
        canc_rate = st.number_input("Cancellation Rate", value=0.0)
        country = st.selectbox("Country", ["United Kingdom", "Germany", "France", "EIRE", "Spain"])

    if st.button("Predict Lapse Risk"):
        payload = {
            "customer_id": c_id,
            "recency_days": recency,
            "frequency_orders": freq,
            "monetary": monetary,
            "average_order_value": aov,
            "average_basket_quantity": abq,
            "distinct_products": distinct_p,
            "tenure_days": tenure,
            "average_days_between_orders": avg_days,
            "orders_last_30d": o_30d,
            "orders_last_90d": o_90d,
            "orders_last_180d": o_180d,
            "spend_last_30d": s_30d,
            "spend_last_90d": s_90d,
            "spend_last_180d": s_180d,
            "cancellation_count": canc_cnt,
            "cancellation_value": canc_val,
            "cancellation_rate": canc_rate,
            "country": country
        }
        try:
            res = requests.post(f"{API_BASE_URL}/predict-lapse", json=payload)
            if res.status_code == 200:
                result = res.json()
                prob = result["lapse_probability"]
                category = result["risk_category"]
                
                if category == "High":
                    st.error(f"⚠️ Churn Risk: **{category}** (Probability: {prob * 100:.2f}%)")
                elif category == "Medium":
                    st.warning(f"⚡ Churn Risk: **{category}** (Probability: {prob * 100:.2f}%)")
                else:
                    st.success(f"✅ Churn Risk: **{category}** (Probability: {prob * 100:.2f}%)")
            else:
                st.error(f"Error: {res.json().get('detail', 'Prediction failed')}")
        except Exception as e:
            st.error(f"Connection error: {e}")

# ---------------- TAB 3: RAG ASSISTANT ----------------
with tab3:
    st.header("Product & Customer Intelligence Assistant")
    query = st.text_input("Ask about product recommendations or customer segments:")
    if st.button("Query RAG System") and query:
        with st.spinner("Retrieving product catalog context..."):
            try:
                res = requests.post(f"{API_BASE_URL}/rag-chat", json={"question": query})
                if res.status_code == 200:
                    st.write("### Response:")
                    st.write(res.json()["answer"])
                else:
                    st.error("RAG Service unavailable.")
            except Exception as e:
                st.error(f"Error: {e}")