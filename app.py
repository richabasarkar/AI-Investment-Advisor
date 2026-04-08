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
    """
    Fetches only the 6 desired fields: Company, Price, P/E, Beta, Debt/Equity, Revenue Growth.
    Uses yf.Ticker.info as the primary source (most reliable for fundamental data)
    and yf.download for the latest close price when fast_info is unavailable.
    TTL=300 ensures data refreshes every 5 minutes.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info  # single reliable call

        # Company name
        name = info.get("shortName") or info.get("longName") or ticker

        # Price: prefer currentPrice, fall back to regularMarketPrice, then last close via download
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            try:
                dl = yf.download(ticker, period="1d", interval="1m", progress=False)
                if not dl.empty:
                    price = round(float(dl["Close"].iloc[-1]), 2)
            except Exception:
                price = None

        # Fundamentals
        pe = info.get("trailingPE") or info.get("forwardPE")
        beta = info.get("beta")
        de_ratio = info.get("debtToEquity")
        rev_growth = info.get("revenueGrowth")

        def fmt(val, pct=False):
            if val is None:
                return "N/A"
            if pct:
                return f"{round(val * 100, 2)}%"
            return round(val, 2)

        metrics = {
            "Company":        name,
            "Price":          fmt(price),
            "P/E":            fmt(pe),
            "Beta":           fmt(beta),
            "Debt/Equity":    fmt(de_ratio),
            "Revenue Growth": fmt(rev_growth, pct=True),
        }

        # Attempt history (6 months) for chart
        try:
            history = stock.history(period="6mo")
            if history.empty:
                history = None
        except Exception:
            history = None

        return metrics, history

    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return {}, None


@st.cache_data(ttl=3600)
def generate_recommendations(risk, horizon, goal, sectors, investment_type, option_types=[]):
    type_instructions = {
        "Stocks": "Recommend individual stocks (equities) only. Use standard stock tickers (e.g. AAPL, MSFT).",
        "ETFs": "Recommend ETFs (Exchange-Traded Funds) only. Use ETF tickers (e.g. VOO, QQQ, ARKK, XLK). Do NOT recommend individual stocks.",
        "Bonds": "Recommend bond ETFs or bond funds only (e.g. BND, TLT, AGG, GOVT, HYG). Do NOT recommend individual stocks or equity ETFs.",
        "Debt Financing": "Recommend fixed-income instruments and debt-focused funds only, such as corporate bond ETFs, treasury funds, or BDCs (e.g. BND, LQD, BIZD, ARCC). Do NOT recommend equity stocks.",
        "Options": f"Recommend options based on user preference. Focus on types: {', '.join(option_types) if option_types else 'any option type'}."
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
- Option Type(s): {', '.join(option_types) if option_types else 'N/A'}
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
            model="gpt-4o-mini",
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

@st.cache_data(ttl=3600)
def generate_single_analysis(ticker, risk, horizon, goal, sectors, investment_type, option_types=[]):
    """Generate an AI analysis for a manually entered ticker using the user's profile."""
    sector_note = f"Focus on these sectors: {', '.join(sectors)}." if sectors else "No specific sector preference."

    prompt = f"""
You are an expert financial advisor. A user has manually entered the ticker "{ticker}" and wants an analysis based on their investment profile.

USER PROFILE:
- Risk Tolerance: {risk}
- Investment Horizon: {horizon}
- Investment Goal: {goal}
- Investment Type: {investment_type}
- Option Type(s): {', '.join(option_types) if option_types else 'N/A'}
- Sector Preference: {sector_note}

Analyse "{ticker}" against this profile and return ONLY a valid JSON object — no markdown, no preamble.

OUTPUT FORMAT:
{{
  "Recommendation": "Buy" or "Hold" or "Avoid",
  "Reasoning": "Detailed reasoning tied to the user profile.",
  "Risk Rating": "Low" or "Medium" or "High",
  "Alignment with Goals": "Explanation of how this aligns (or doesn't) with the user's goal."
}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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

    recs = generate_recommendations(risk, horizon, goal, tuple(sector), investment_type, option_types)

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
    current_ticker = st.session_state.last_ticker
    if current_ticker:
        data, history = get_stock_data(current_ticker)

        if not data:
            st.error(f"No data found for {current_ticker}. Make sure the ticker is valid.")
        else:
            st.markdown(f"### 📈 Data for {current_ticker}")

            # Show all 6 metrics in a single row
            metric_keys = list(data.keys())
            cols = st.columns(len(metric_keys))
            for j, key in enumerate(metric_keys):
                cols[j].metric(label=key, value=data[key])

            # Show chart if available
            if history is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close"))
                fig.update_layout(
                    title=f"{current_ticker} 6-Month Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#111111"),
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No historical data available for chart.")

# -----------------------
# AI Analysis Tab
# -----------------------
with tab2:
    if st.session_state.last_ticker:
        current_ticker = st.session_state.last_ticker
        cached_analysis = st.session_state.rec_analysis_cache.get(current_ticker)

        if cached_analysis:
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
            st.markdown(f"### Analysis for {current_ticker}")
            st.caption("Generating analysis based on your investment profile...")

            with st.spinner(f"Analysing {current_ticker}..."):
                generated = generate_single_analysis(
                    current_ticker, risk, horizon, goal,
                    tuple(sector), investment_type, option_types
                )

            if isinstance(generated, dict) and "error" in generated:
                st.error(f"Could not generate analysis: {generated['error']}")
            else:
                # Cache it so Chat tab and subsequent views can use it
                st.session_state.rec_analysis_cache[current_ticker] = generated

                verdict = generated.get("Recommendation", "Hold")
                badge_class = {"Buy": "badge-buy", "Hold": "badge-hold", "Avoid": "badge-avoid"}.get(verdict, "badge-hold")

                st.markdown(f'<span class="{badge_class}">{verdict}</span>', unsafe_allow_html=True)
                st.markdown("---")

                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-label">Reasoning</div>
                    <div class="analysis-value">{generated.get("Reasoning", "N/A")}</div>
                </div>
                <div class="analysis-card">
                    <div class="analysis-label">Risk Rating</div>
                    <div class="analysis-value">{generated.get("Risk Rating", "N/A")}</div>
                </div>
                <div class="analysis-card">
                    <div class="analysis-label">Alignment with Goals</div>
                    <div class="analysis-value">{generated.get("Alignment with Goals", "N/A")}</div>
                </div>
                """, unsafe_allow_html=True)

# -----------------------
# Chat Tab
# -----------------------
with tab3:
    st.markdown("### 💬 Ask About This Investment")

    current_ticker = st.session_state.last_ticker

    # Build a rich context string from live stock data and cached AI analysis
    def build_chat_context(ticker):
        context_parts = []

        if ticker:
            context_parts.append(f"The user is currently viewing the stock ticker: {ticker}.")

            # Stock metrics context
            stock_data, _ = get_stock_data(ticker)
            if stock_data:
                metrics_str = ", ".join(
                    f"{k}: {v}" for k, v in stock_data.items()
                )
                context_parts.append(f"Live stock data for {ticker} — {metrics_str}.")

            # AI analysis context
            analysis = st.session_state.rec_analysis_cache.get(ticker)
            if analysis:
                context_parts.append(
                    f"AI analysis for {ticker}: "
                    f"Recommendation: {analysis.get('Recommendation', 'N/A')}. "
                    f"Reasoning: {analysis.get('Reasoning', 'N/A')}. "
                    f"Risk Rating: {analysis.get('Risk Rating', 'N/A')}. "
                    f"Alignment with Goals: {analysis.get('Alignment with Goals', 'N/A')}."
                )

        # User profile context
        context_parts.append(
            f"User investment profile — Risk Tolerance: {risk}, "
            f"Investment Horizon: {horizon}, Goal: {goal}, "
            f"Investment Type: {investment_type}, "
            f"Preferred Sectors: {', '.join(sector) if sector else 'None specified'}."
        )

        return " ".join(context_parts)

    chat_input = st.text_input("Ask a question about this investment...", key="chat_input")

    if chat_input:
        st.session_state.chat_history.append({"role": "user", "content": chat_input})

        context = build_chat_context(current_ticker)

        system_prompt = (
            "You are a helpful AI financial assistant. "
            "Answer questions using the context below — prioritise this data over general knowledge when relevant. "
            "Be concise, clear, and helpful.\n\n"
            f"CONTEXT:\n{context}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages += st.session_state.chat_history

        try:
            resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            answer = resp.choices[0].message.content
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"Error generating response: {e}")

    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.markdown(f"**You:** {chat['content']}")
        else:
            st.markdown(f"**AI:** {chat['content']}")