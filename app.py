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

# Reset chat history if ticker changed
if "last_ticker" not in st.session_state or st.session_state.last_ticker != ticker:
    st.session_state.chat_history = []
    st.session_state.last_ticker = ticker

# -----------------------
# Data Functions
# -----------------------
@st.cache_data(ttl=300)  # refresh every 5 minutes
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
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content.strip()
        return json.loads(text_response)
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600)
def generate_recommendations(profile):
    prompt = f"""
You are an AI investment advisor.

User Profile:
{profile}

Suggest 5 stocks that match this profile.

Return ONLY valid JSON in this format:
[
  {{"ticker": "AAPL", "company": "Apple Inc."}},
  {{"ticker": "MSFT", "company": "Microsoft Corporation"}}
]
"""
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
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
        tab0, tab1, tab2, tab3 = st.tabs(["Recommendations", "Stock Data", "AI Analysis", "Chat"])

        # -----------------------
        # Recommendations Tab
        # -----------------------
        with tab0:
            st.markdown("### 📊 Recommended Stocks For You")

            recs = generate_recommendations(str(user_profile))

            if isinstance(recs, dict) and "error" in recs:
                st.error(recs["error"])
            else:
                cols = st.columns(5)

                for i, stock in enumerate(recs):
                    ticker_symbol = stock.get("ticker", "N/A")
                    company_name = stock.get("company", "N/A")

                    with cols[i]:
                        st.markdown(f"""
                        <div class="analysis-card">
                            <div class="analysis-label">{ticker_symbol}</div>
                            <div class="analysis-value">{company_name}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Analyze {ticker_symbol}", key=f"rec_{i}"):
                            st.session_state.last_ticker = ticker_symbol
                            st.session_state.chat_history = []
                            st.experimental_rerun()
        # -----------------------
        # Stock Data Tab
        # -----------------------
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

        # -----------------------
        # AI Analysis Tab
        # -----------------------
        with tab2:
            if st.button("Analyze"):
                analysis = generate_response(str(user_profile), str(data), ticker)
                if "error" in analysis:
                    st.error(analysis["error"])
                else:
                    st.markdown(f"Recommendation: {analysis.get('Recommendation', 'N/A')}")
                    st.write(analysis.get("Reasoning", "N/A"))

                    st.markdown(f"Risk Rating")
                    st.write(analysis.get("Risk Rating", "N/A"))

                    st.markdown(f"Alignment with Goals")
                    st.write(analysis.get("Alignment with Goals", "N/A"))

        # -----------------------
        # Chat Tab
        # -----------------------
        with tab3:
            st.markdown("### Ask about this stock")
            user_q = st.text_input("Type your question here:")

            if st.button("Send Question"):
                if not user_q:
                    st.warning("Please enter a question first!")
                else:
                    # Initialize chat history if not already
                    if "chat_history" not in st.session_state:
                        st.session_state.chat_history = []

                    # Build context prompt
                    context_prompt = f"""
You are an AI investment analyst.

User Profile:
{user_profile}

Stock Ticker: {ticker}
Stock Data:
{data}
"""

                    # Add previous chat messages
                    chat_messages = [{"role": "system", "content": context_prompt}]
                    for msg in st.session_state.chat_history:
                        chat_messages.append(msg)

                    # Add current user question
                    chat_messages.append({"role": "user", "content": user_q})

                    # Get AI response
                    try:
                        response = client.chat.completions.create(
                            model="gpt-5-mini",
                            messages=chat_messages
                        )
                        answer = response.choices[0].message.content

                        # Save question & answer to chat history
                        st.session_state.chat_history.append({"role": "user", "content": user_q})
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})

                        st.markdown("**AI Response:**")
                        st.write(answer)

                    except Exception as e:
                        st.error(f"Error generating response: {e}")