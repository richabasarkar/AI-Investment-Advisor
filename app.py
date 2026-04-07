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
        display: flex;
        justify-content: center;
        gap: 20px;
        background-color: #ffffff;
        border-radius: 14px;
        padding: 10px;
        border: 1px solid #e2e6ef;
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #f1f3f8;
        color: #444;
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e4e8f2;
        color: #000;
    }

    .stTabs [aria-selected="true"] {
        background-color: #dfe6f3 !important;
        color: #000 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
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
ticker_input = st.text_input("🔍 Enter a stock ticker (e.g., AAPL, TSLA, MSFT)",
                             value=st.session_state.get("ticker_input", ""))
ticker = ticker_input.upper().strip() if ticker_input else ""

if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ticker
    st.session_state.chat_history = []
    st.session_state.active_tab = 0
    st.session_state.rec_analysis_cache = {}
else:
    if ticker and ticker != st.session_state.last_ticker:
        st.session_state.last_ticker = ticker
        st.session_state.chat_history = []
        st.session_state.active_tab = 0

if "rec_analysis_cache" not in st.session_state:
    st.session_state.rec_analysis_cache = {}

# -----------------------
# Data Functions
# -----------------------
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)

        # Fetch fast_info for reliable metrics
        fi = getattr(stock, "fast_info", {})
        last_price = fi.get("last_price", "N/A")
        prev_close = fi.get("previous_close", "N/A")
        day_high = fi.get("day_high", "N/A")
        day_low = fi.get("day_low", "N/A")
        open_price = fi.get("open", "N/A")
        beta = fi.get("beta", "N/A")

        # Fetch info for supplemental metrics
        info = getattr(stock, "info", {})
        name = info.get("shortName") or info.get("longName") or ticker
        pe = info.get("trailingPE", "N/A")
        de_ratio = info.get("debtToEquity", "N/A")
        rev_growth = info.get("revenueGrowth", "N/A")

        metrics = {
            "Company": name,
            "Price": last_price,
            "Open": open_price,
            "High": day_high,
            "Low": day_low,
            "Previous Close": prev_close,
            "P/E": pe,
            "Beta": beta,
            "Debt/Equity": de_ratio,
            "Revenue Growth": rev_growth
        }

        # Fetch history for chart only (optional)
        try:
            history = stock.history(period="6mo")
            if history.empty:
                history = None
        except:
            history = None

        return metrics, history
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return {}, None