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
def generate_recommendations(risk, horizon, goal, sectors, investment_type):
    type_instructions = {
        "Stocks": "Recommend individual stocks (equities) only. Use standard stock tickers (e.g. AAPL, MSFT).",
        "ETFs": "Recommend ETFs (Exchange-Traded Funds) only. Use ETF tickers (e.g. VOO, QQQ, ARKK, XLK). Do NOT recommend individual stocks.",
        "Bonds": "Recommend bond ETFs or bond funds only (e.g. BND, TLT, AGG, GOVT, HYG). Do NOT recommend individual stocks or equity ETFs.",
        "Debt Financing": "Recommend fixed-income instruments and debt-focused funds only, such as corporate bond ETFs, treasury funds, or BDCs (e.g. BND, LQD, BIZD, ARCC). Do NOT recommend equity stocks."
    }

    sector_note = f"Focus on these sectors: {', '.join(sectors)}." if sectors else "No specific sector preference — diversify across sectors."

    risk_guidance = {
        "Low": "Prioritize capital preservation and low volatility. Avoid speculative or high-beta assets.",
        "Medium": "Balance growth and stability. Moderate volatility is acceptable.",
        "High": "Prioritize high growth potential. Volatility and risk are acceptable."
    }

    horizon_guidance = {
        "Short": "Investment horizon is short-term (under 1 year). Prefer liquid, lower-duration assets.",
        "Medium": "Investment horizon is medium-term (1–5 years). Balance between growth and stability.",
        "Long": "Investment horizon is long-term (5+ years). Growth-oriented assets with compounding potential are preferred."
    }

    goal_guidance = {
        "Growth": "The user wants capital appreciation above all else.",
        "Stable Income": "The user wants consistent dividends or interest income.",
        "Capital Preservation": "The user wants to protect their principal from loss."
    }

    prompt = f"""
You are an expert financial advisor helping a beginner investor find their first investments.

USER PROFILE:
- Investment Type: {investment_type}
- Risk Tolerance: {risk} — {risk_guidance.get(risk, '')}
- Investment Horizon: {horizon} — {horizon_guidance.get(horizon, '')}
- Investment Goal: {goal} — {goal_guidance.get(goal, '')}
- Sector Preference: {sector_note}

STRICT RULES:
1. {type_instructions.get(investment_type, 'Recommend appropriate securities.')}
2. All recommendations MUST match the investment type above. This is non-negotiable.
3. Recommend exactly 5 options that genuinely fit this user's profile.
4. For EACH recommendation, you must also provide:
   - A "recommendation" verdict: ONLY "Buy" or "Hold" (never "Avoid" — if you would avoid it, pick a different one)
   - A "reasoning" field explaining why it fits this specific user's profile
   - A "risk_rating" of Low, Medium, or High
   - An "alignment" field explaining how it aligns with the user's goal
   - A one-sentence "reason" summary for the card display
5. Every ticker you return must be one you are genuinely recommending as Buy or Hold for this user. Do not include anything you would tell this user to avoid.
6. Return ONLY a valid JSON array — no markdown, no explanation, no preamble.

OUTPUT FORMAT:
[
  {{
    "ticker": "TICKER",
    "company": "Full Name",
    "reason": "One sentence why this fits the user.",
    "recommendation": "Buy",
    "reasoning": "Detailed reasoning tied to the user profile.",
    "risk_rating": "Low",
    "alignment": "Explanation of how this aligns with the user's goal."
  }},
  ...
]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content.strip()
        if text_response.startswith("```"):
            text_response = text_response.split("```")[1]
            if text_response.startswith("json"):
                text_response = text_response[4:]
        return json.loads(text_response.strip())
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Tabs
# -----------------------
tab_labels = ["Recommendations", "Stock Data", "AI Analysis", "Chat"]
tab0, tab1, tab2, tab3 = st.tabs(tab_labels)

# -----------------------
# Recommendations Tab
# -----------------------
with tab0:
    st.markdown("### 📊 Recommended for You")
    st.caption(f"Based on: **{investment_type}** · **{risk} Risk** · **{horizon}-term** · **{goal}**")

    recs = generate_recommendations(risk, horizon, goal, tuple(sector), investment_type)

    if isinstance(recs, dict) and "error" in recs:
        st.error(f"Could not generate recommendations: {recs['error']}")
    else:
        for stock in recs:
            t = stock.get("ticker")
            if t and t not in st.session_state.rec_analysis_cache:
                st.session_state.rec_analysis_cache[t] = {
                    "Recommendation": stock.get("recommendation", "Hold"),
                    "Reasoning": stock.get("reasoning", ""),
                    "Risk Rating": stock.get("risk_rating", ""),
                    "Alignment with Goals": stock.get("alignment", "")
                }

        badge_map = {"Buy": "badge-buy", "Hold": "badge-hold", "Avoid": "badge-avoid"}

        for i, stock in enumerate(recs[:5]):
            ticker_symbol = stock.get("ticker", "N/A")
            company_name = stock.get("company", "N/A")
            reason = stock.get("reason", "")
            verdict = stock.get("recommendation", "Hold")
            badge_class = badge_map.get(verdict, "badge-hold")

            col_badge, col_ticker, col_name, col_reason, col_btn = st.columns([1, 1, 2, 4, 1.2])

            with col_badge:
                st.markdown(f'<div style="padding-top:8px"><span class="{badge_class}">{verdict}</span></div>', unsafe_allow_html=True)
            with col_ticker:
                st.markdown(f'<div style="padding-top:10px; font-weight:700; font-size:1rem;">{ticker_symbol}</div>', unsafe_allow_html=True)
            with col_name:
                st.markdown(f'<div style="padding-top:10px; color:#444;">{company_name}</div>', unsafe_allow_html=True)
            with col_reason:
                st.markdown(f'<div style="padding-top:10px; font-size:0.85rem; color:#555;">{reason}</div>', unsafe_allow_html=True)
            with col_btn:
                if st.button(f"Select", key=f"rec_{i}"):
                    st.session_state.last_ticker = ticker_symbol
                    st.session_state.ticker_input = ticker_symbol
                    st.session_state.chat_history = []
                    st.rerun()

            st.markdown("<hr style='margin: 6px 0; border-color:#e2e6ef;'>", unsafe_allow_html=True)

# -----------------------
# Stock Data Tab
# -----------------------
with tab1:
    if st.session_state.last_ticker:
        data, history = get_stock_data(st.session_state.last_ticker)
        if data is None:
            st.error(f"No valid data found for {st.session_state.last_ticker}")
        else:
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
                fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines"))
                fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font=dict(color="#111111"))
                st.plotly_chart(fig, use_container_width=True)

# -----------------------
# AI Analysis Tab
# -----------------------
with tab2:
    if st.session_state.last_ticker:
        current_ticker = st.session_state.last_ticker
        cached_analysis = st.session_state.rec_analysis_cache.get(current_ticker)

        if cached_analysis:
            # Show the pre-computed analysis from the recommendation step
            st.markdown(f"### Analysis for {current_ticker}")
            st.caption("This analysis was generated alongside the recommendation to ensure consistency.")

            verdict = cached_analysis.get("Recommendation", "Hold")
            badge_class = {"Buy": "badge-buy", "Hold": "badge-hold", "Avoid": "badge-avoid"}.get(verdict, "badge-hold")

            st.markdown(f'<span class="{badge_class}">{verdict}</span>', unsafe_allow_html=True)
            st.markdown("---")

            st.markdown(f"""
            <div class="analysis-card">
                <div class="analysis-label">Reasoning</div>
                <div class="analysis-value">{cached_analysis.get("Reasoning", "N/A")}</div>
            </div>
            <div class="analysis-card">
                <div class="analysis-label">Risk Rating</div>
                <div class="analysis-value">{cached_analysis.get("Risk Rating", "N/A")}</div>
            </div>
            <div class="analysis-card">
                <div class="analysis-label">Alignment with Goals</div>
                <div class="analysis-value">{cached_analysis.get("Alignment with Goals", "N/A")}</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # Ticker was manually entered, not from recommendations — run fresh analysis
            st.markdown(f"### Analysis for {current_ticker}")
            st.caption("This ticker was entered manually. Running a fresh analysis.")

            if st.button("Analyze"):
                data, _ = get_stock_data(current_ticker)
                if data is None:
                    st.error("Could not fetch stock data for analysis.")
                else:
                    prompt = f"""
You are an AI investment analyst.

User Profile:
{user_profile}

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
                        analysis = json.loads(text_response)
                        st.session_state.rec_analysis_cache[current_ticker] = analysis

                        verdict = analysis.get("Recommendation", "Hold")
                        badge_class = {"Buy": "badge-buy", "Hold": "badge-hold", "Avoid": "badge-avoid"}.get(verdict, "badge-hold")
                        st.markdown(f'<span class="{badge_class}">{verdict}</span>', unsafe_allow_html=True)
                        st.markdown("---")
                        st.markdown(f"""
                        <div class="analysis-card">
                            <div class="analysis-label">Reasoning</div>
                            <div class="analysis-value">{analysis.get("Reasoning", "N/A")}</div>
                        </div>
                        <div class="analysis-card">
                            <div class="analysis-label">Risk Rating</div>
                            <div class="analysis-value">{analysis.get("Risk Rating", "N/A")}</div>
                        </div>
                        <div class="analysis-card">
                            <div class="analysis-label">Alignment with Goals</div>
                            <div class="analysis-value">{analysis.get("Alignment with Goals", "N/A")}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error generating analysis: {e}")

# -----------------------
# Chat Tab
# -----------------------
with tab3:
    if st.session_state.last_ticker:
        st.markdown("### Ask about this stock")
        user_q = st.text_input("Type your question here:")

        if st.button("Send Question"):
            if not user_q:
                st.warning("Please enter a question first!")
            else:
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = []

                data, _ = get_stock_data(st.session_state.last_ticker)

                context_prompt = f"""
You are an AI investment analyst.

User Profile:
{user_profile}

Stock Ticker: {st.session_state.last_ticker}
Stock Data:
{data}
"""

                chat_messages = [{"role": "system", "content": context_prompt}]
                for msg in st.session_state.chat_history:
                    chat_messages.append(msg)

                chat_messages.append({"role": "user", "content": user_q})

                try:
                    response = client.chat.completions.create(model="gpt-5-mini", messages=chat_messages)
                    answer = response.choices[0].message.content

                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

                    st.markdown("**AI Response:**")
                    st.write(answer)
                except Exception as e:
                    st.error(f"Error generating response: {e}")