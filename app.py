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
# Custom CSS (UNCHANGED)
# -----------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f5f7fb;
        color: #111111;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------
# Initialize OpenAI client
# -----------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------
# Sidebar Inputs (UNCHANGED)
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
    ["Stocks", "ETFs", "Bonds", "Debt Financing", "Options"]
)

option_types = []
if investment_type == "Options":
    option_types = st.sidebar.multiselect(
        "Option Type(s)",
        ["Call", "Put", "Future", "Other"]
    )

user_profile = {
    "risk": risk,
    "horizon": horizon,
    "goal": goal,
    "sector": sector,
    "investment_type": investment_type,
    "option_types": option_types
}

# -----------------------
# Stock Input
# -----------------------
ticker_input = st.text_input("🔍 Enter a stock ticker", value=st.session_state.get("ticker_input", ""))
ticker = ticker_input.upper().strip() if ticker_input else ""

if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ticker
    st.session_state.chat_history = []
    st.session_state.rec_analysis_cache = {}

# -----------------------
# ✅ FIXED STOCK DATA FUNCTION
# -----------------------
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)

        fast_info = getattr(stock, "fast_info", {})
        info = getattr(stock, "info", {})

        price = fast_info.get("last_price") or info.get("currentPrice")
        pe = info.get("trailingPE")
        beta = info.get("beta")
        de = info.get("debtToEquity")
        rev = info.get("revenueGrowth")
        name = info.get("longName") or info.get("shortName") or ticker

        metrics = {
            "Company": name,
            "Price": round(price, 2) if price else "N/A",
            "P/E": round(pe, 2) if pe else "N/A",
            "Beta": round(beta, 2) if beta else "N/A",
            "Debt/Equity": round(de, 2) if de else "N/A",
            "Revenue Growth": round(rev, 2) if rev else "N/A"
        }

        history = stock.history(period="6mo")
        if history.empty:
            history = None

        return metrics, history

    except:
        return {}, None

# -----------------------
# Tabs (UNCHANGED)
# -----------------------
tab0, tab1, tab2, tab3 = st.tabs(["Recommendations", "Stock Data", "AI Analysis", "Chat"])

# -----------------------
# Stock Data Tab (UPDATED DISPLAY ONLY)
# -----------------------
with tab1:
    current_ticker = st.session_state.last_ticker

    if current_ticker:
        data, history = get_stock_data(current_ticker)

        if not data:
            st.error(f"No data found for {current_ticker}")
        else:
            st.markdown(f"### 📈 Data for {current_ticker}")

            col1, col2, col3, col4, col5, col6 = st.columns(6)

            col1.metric("Company", data["Company"])
            col2.metric("Price", data["Price"])
            col3.metric("P/E", data["P/E"])
            col4.metric("Beta", data["Beta"])
            col5.metric("Debt/Equity", data["Debt/Equity"])
            col6.metric("Revenue Growth", data["Revenue Growth"])

            if history is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines"))
                st.plotly_chart(fig, use_container_width=True)

# -----------------------
# Chat Tab (✅ FIXED CONTEXT)
# -----------------------
with tab3:
    st.markdown("### 💬 Ask About This Investment")

    chat_input = st.text_input("Ask a question...", key="chat_input")

    if chat_input and st.session_state.last_ticker:
        current_ticker = st.session_state.last_ticker
        data, _ = get_stock_data(current_ticker)
        analysis = st.session_state.rec_analysis_cache.get(current_ticker, {})

        # ✅ FULL CONTEXT PROMPT
        context = f"""
You are an AI investment assistant.

USER PROFILE:
{user_profile}

CURRENT TICKER: {current_ticker}

STOCK DATA:
{data}

AI ANALYSIS:
{analysis}

Answer the user's question using ALL the above context.
"""

        st.session_state.chat_history.append({"role": "user", "content": chat_input})

        messages = [{"role": "system", "content": context}]
        messages += st.session_state.chat_history

        try:
            resp = client.chat.completions.create(
                model="gpt-5-mini",
                messages=messages
            )
            answer = resp.choices[0].message.content

            st.session_state.chat_history.append({"role": "assistant", "content": answer})

        except Exception as e:
            st.error(f"Error: {e}")

    # Display chat
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.markdown(f"**You:** {chat['content']}")
        else:
            st.markdown(f"**AI:** {chat['content']}")