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
# Custom CSS (LIGHT THEME)
# -----------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f5f7fb;
        color: #111111;
    }

    .header-banner {
        background: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 16px;
        padding: 36px 40px;
        margin-bottom: 32px;
    }
    .header-banner h1 {
        font-size: 2.4rem;
        font-weight: 700;
        color: #111111;
    }
    .header-banner p {
        color: #555;
    }

    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #111111;
    }

    .analysis-card {
        background-color: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 16px;
    }
    .analysis-label {
        font-size: 0.75rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .analysis-value {
        font-size: 1rem;
        color: #222;
        line-height: 1.6;
    }

    .badge-buy {
        background-color: #e6f4ea;
        color: #1e7e34;
        border: 1px solid #1e7e34;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .badge-avoid {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #721c24;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .badge-hold {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #856404;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        border-radius: 12px;
        padding: 6px;
        border: 1px solid #e2e6ef;
    }
    .stTabs [data-baseweb="tab"] {
        color: #666;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e9eef6 !important;
        color: #111 !important;
    }

    .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 1px solid #ccc;
        color: #111111;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 1rem;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e6ef;
    }

    hr {
        border-color: #e2e6ef;
    }

    [data-testid="stChatMessage"] {
        background-color: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 12px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------
# Initialize OpenAI client
# -----------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------
# Header Banner
# -----------------------
st.markdown("""
<div class="header-banner">
    <h1>📈 AI Investment Advisor</h1>
    <p>Enter a stock ticker to get real-time data, AI-powered analysis, and personalized insights based on your investment profile.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------
# Sidebar Inputs
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
# Stock Input
# -----------------------
ticker_input = st.text_input("🔍 Enter a stock ticker (e.g., AAPL, TSLA, MSFT)")
ticker = ticker_input.upper().strip() if ticker_input else ""

if "last_ticker" not in st.session_state or st.session_state.last_ticker != ticker:
    st.session_state.chat_history = []
    st.session_state.last_ticker = ticker

# -----------------------
# Data Functions
# -----------------------
@st.cache_data
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

@st.cache_data
def generate_response(profile, data, ticker):
    prompt = f"""
You are an AI investment analyst.

User Profile:
{profile}

Stock Data:
{data}

Return ONLY valid JSON:
{{
  "Recommendation": "Buy / Hold / Avoid",
  "Reasoning": "...",
  "Risk Rating": "Low / Medium / High",
  "Alignment with Goals": "..."
}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content.strip()
        return json.loads(text_response)
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Main App
# -----------------------
if ticker:
    data, history = get_stock_data(ticker)

    if data is None:
        st.error(f"No valid data found for {ticker}")
    else:
        tab1, tab2, tab3 = st.tabs(["Stock Data", "AI Analysis", "Chat"])

        with tab1:
            col1, col2, col3, col4, col5 = st.columns(5)

            def fmt(val):
                return round(val, 2) if val else "N/A"

            col1.metric("Price", f"${fmt(data['Price'])}")
            col2.metric("P/E", fmt(data["Price to Earnings Ratio"]))
            col3.metric("Beta", fmt(data["Beta"]))
            col4.metric("Debt/Equity", fmt(data["Debt to Equity Ratio"]))
            col5.metric("Revenue Growth", fmt(data["Revenue Growth"]))

            if history is not None and not history.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history.index,
                    y=history["Close"],
                    mode="lines"
                ))
                fig.update_layout(
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#111111")
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            if st.button("Analyze"):
                analysis = generate_response(str(user_profile), str(data), ticker)
                st.json(analysis)

        with tab3:
            user_q = st.text_input("Ask about this stock")
            if user_q:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": user_q}]
                )
                st.write(response.choices[0].message.content)