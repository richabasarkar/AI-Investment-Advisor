import streamlit as st
import yfinance as yf
from openai import OpenAI
import os
import json
import plotly.graph_objects as go

# -----------------------
# Page Config
# -----------------------
st.set_page_config(
    page_title="AI Investment Advisor",
    page_icon="📈",
    layout="wide"
)

# -----------------------
# Session State Init
# -----------------------
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = ""

if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ""

# -----------------------
# Custom CSS
# -----------------------
st.markdown("""<style>
.stApp { background-color: #f5f7fb; color: #111; }
.header-banner { background:#fff; border:1px solid #e2e6ef; border-radius:16px; padding:36px 40px; margin-bottom:32px;}
.analysis-card { background:#fff; border:1px solid #e2e6ef; border-radius:12px; padding:20px; margin-bottom:10px;}
.stTabs [data-baseweb="tab-list"] { gap:20px; background:#fff; border-radius:14px; padding:10px; border:1px solid #e2e6ef;}
</style>""", unsafe_allow_html=True)

# -----------------------
# OpenAI Client
# -----------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------
# Header
# -----------------------
st.markdown("""
<div class="header-banner">
<h1>📈 AI Investment Advisor</h1>
<p>Discover, analyze, and explore stocks personalized to your preferences.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------
# Sidebar
# -----------------------
st.sidebar.markdown("## Your Preferences")

risk = st.sidebar.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
horizon = st.sidebar.selectbox("Investment Horizon", ["Short", "Medium", "Long"])
goal = st.sidebar.selectbox("Investment Goal", ["Growth", "Stable Income", "Capital Preservation"])
sector = st.sidebar.multiselect(
    "Preferred Sectors",
    ["Technology", "Healthcare", "Finance", "Energy", "Consumer Goods"]
)
investment_type = st.sidebar.selectbox(
    "Investment Type",
    ["Stocks", "ETFs", "Bonds", "Debt Financing"]
)

user_profile = {
    "risk": risk,
    "horizon": horizon,
    "goal": goal,
    "sector": sector,
    "investment_type": investment_type
}

# -----------------------
# Stock Input (CONNECTED)
# -----------------------
ticker_input = st.text_input(
    "🔍 Enter a stock ticker (e.g., AAPL, TSLA, MSFT)",
    value=st.session_state.selected_ticker
)

ticker = ticker_input.upper().strip() if ticker_input else ""

# Reset chat when ticker changes
if ticker != st.session_state.last_ticker:
    st.session_state.chat_history = []
    st.session_state.last_ticker = ticker

# -----------------------
# Data Functions
# -----------------------
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if "currentPrice" not in info:
            return None, None
        metrics = {
            "Price": info.get("currentPrice"),
            "Price to Earnings Ratio": info.get("trailingPE"),
            "Beta": info.get("beta"),
            "Debt to Equity Ratio": info.get("debtToEquity"),
            "Revenue Growth": info.get("revenueGrowth")
        }
        history = stock.history(period="6mo")
        return metrics, history
    except:
        return None, None

@st.cache_data(ttl=3600)
def generate_response(profile, data, ticker):
    prompt = f"""
User Profile: {profile}
Stock Data: {data}

Return JSON:
{{
"Recommendation":"Buy/Hold/Avoid",
"Reasoning":"...",
"Risk Rating":"Low/Medium/High",
"Alignment with Goals":"..."
}}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600)
def generate_recommendations(profile):
    prompt = f"""
User Profile: {profile}
Suggest 5 stocks.

Return JSON list:
[{{"ticker":"AAPL","company":"Apple Inc."}}]
"""
    try:
        res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Tabs (ALWAYS VISIBLE)
# -----------------------
tab0, tab1, tab2, tab3 = st.tabs(
    ["Recommendations", "Stock Data", "AI Analysis", "Chat"]
)

# -----------------------
# Recommendations (HOME)
# -----------------------
with tab0:
    st.markdown("### 📊 Recommended Stocks For You")

    recs = generate_recommendations(str(user_profile))

    if isinstance(recs, dict):
        st.error(recs["error"])
    else:
        for i, stock in enumerate(recs):
            t = stock.get("ticker")
            c = stock.get("company")

            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"""
                <div class="analysis-card">
                <b>{t}</b><br>{c}
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("Select", key=f"sel_{i}"):
                    st.session_state.selected_ticker = t
                    st.session_state.active_tab = 1  # go to Stock Data
                    st.rerun()

# -----------------------
# Stock Data
# -----------------------
with tab1:
    if not ticker:
        st.info("Select a stock from Recommendations.")
    else:
        data, history = get_stock_data(ticker)

        if data is None:
            st.error("No data found.")
        else:
            cols = st.columns(5)

            def fmt(v): return round(v, 2) if v else "N/A"

            cols[0].metric("Price", f"${fmt(data['Price'])}")
            cols[1].metric("P/E", fmt(data["Price to Earnings Ratio"]))
            cols[2].metric("Beta", fmt(data["Beta"]))
            cols[3].metric("Debt/Equity", fmt(data["Debt to Equity Ratio"]))
            cols[4].metric("Revenue Growth", fmt(data["Revenue Growth"]))

            if history is not None and not history.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history.index,
                    y=history["Close"],
                    mode="lines"
                ))
                st.plotly_chart(fig, use_container_width=True)

# -----------------------
# AI Analysis
# -----------------------
with tab2:
    if not ticker:
        st.info("Select a stock first.")
    else:
        if st.button("Analyze"):
            analysis = generate_response(str(user_profile), str(data), ticker)

            if "error" in analysis:
                st.error(analysis["error"])
            else:
                st.write(analysis)

# -----------------------
# Chat
# -----------------------
with tab3:
    if not ticker:
        st.info("Select a stock first.")
    else:
        q = st.text_input("Ask about this stock")

        if st.button("Send"):
            msgs = [{"role": "system", "content": f"{user_profile} {data}"}]
            msgs += st.session_state.chat_history
            msgs.append({"role": "user", "content": q})

            res = client.chat.completions.create(
                model="gpt-5-mini",
                messages=msgs
            )

            ans = res.choices[0].message.content

            st.session_state.chat_history.append({"role": "user", "content": q})
            st.session_state.chat_history.append({"role": "assistant", "content": ans})

            st.write(ans)