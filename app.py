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
# Custom CSS
# -----------------------
st.markdown("""
<style>
    /* Background and text */
    .stApp {
        background-color: #0f1117;
        color: #e0e0e0;
    }

    /* Header banner */
    .header-banner {
        background: linear-gradient(135deg, #1a1f2e, #243044);
        border: 1px solid #2e3a52;
        border-radius: 16px;
        padding: 36px 40px;
        margin-bottom: 32px;
    }
    .header-banner h1 {
        font-size: 2.4rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-banner p {
        color: #7a8fa6;
        font-size: 1rem;
        margin-top: 8px;
    }

    /* Metric cards */
    .metric-card {
        background-color: #1a1f2e;
        border: 1px solid #2e3a52;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #7a8fa6;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
    }

    /* Analysis card */
    .analysis-card {
        background-color: #1a1f2e;
        border: 1px solid #2e3a52;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 16px;
    }
    .analysis-label {
        font-size: 0.75rem;
        color: #7a8fa6;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .analysis-value {
        font-size: 1rem;
        color: #e0e0e0;
        line-height: 1.6;
    }

    /* Recommendation badge */
    .badge-buy {
        background-color: #1a3a2a;
        color: #4caf82;
        border: 1px solid #4caf82;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    .badge-avoid {
        background-color: #3a1a1a;
        color: #e05c5c;
        border: 1px solid #e05c5c;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    .badge-hold {
        background-color: #2e2a14;
        color: #e0b84c;
        border: 1px solid #e0b84c;
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1a1f2e;
        border-radius: 12px;
        padding: 6px;
        border: 1px solid #2e3a52;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #7a8fa6;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #243044 !important;
        color: #ffffff !important;
    }

    /* Input */
    .stTextInput > div > div > input {
        background-color: #1a1f2e;
        border: 1px solid #2e3a52;
        color: #ffffff;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 1rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #13161f;
        border-right: 1px solid #2e3a52;
    }

    /* Divider */
    hr {
        border-color: #2e3a52;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background-color: #1a1f2e;
        border: 1px solid #2e3a52;
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

# Reset chat history if ticker changes
if "last_ticker" not in st.session_state or st.session_state.last_ticker != ticker:
    st.session_state.chat_history = []
    st.session_state.last_ticker = ticker

# -----------------------
# Data + AI Functions
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
You are an AI investment analyst. User wants personalized advice.

User Profile:
{profile}

Stock Data:
{data}

Return a structured JSON response EXACTLY in this format:
{{
  "Recommendation": "Buy / Hold / Avoid",
  "Reasoning": "Explain why this stock fits the user profile",
  "Risk Rating": "Low / Medium / High",
  "Alignment with Goals": "How well it matches user's goal, risk, horizon, and investment type"
}}

Strictly use JSON, do not add explanations outside JSON.

Prioritize:
- Low-risk options for users with Low risk tolerance
- Debt financing options if user selected Debt Financing
- Long-term growth if user horizon is Long
"""
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content.strip()
        if not text_response:
            return {"error": "AI returned empty response", "raw_response": None}
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            return {"error": "AI returned invalid JSON", "raw_response": text_response}
    except Exception as e:
        return {"error": f"AI response error: {e}", "raw_response": None}

# -----------------------
# Main Content
# -----------------------
if ticker:
    data, history = get_stock_data(ticker)

    if data is None:
        st.error(f"❌ No valid data found for **{ticker}**. Please check the ticker and try again.")
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Stock Data", "🤖 AI Analysis", "💬 Ask a Question"])

        # -----------------------
        # Tab 1: Stock Data
        # -----------------------
        with tab1:
            st.markdown("### Market Snapshot")

            col1, col2, col3, col4, col5 = st.columns(5)

            def fmt(val, prefix="", suffix=""):
                return f"{prefix}{round(val, 2)}{suffix}" if val is not None else "N/A"

            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Price</div>
                    <div class="metric-value">{fmt(data['Price'], prefix="$")}</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">P/E Ratio</div>
                    <div class="metric-value">{fmt(data['Price to Earnings Ratio'])}</div>
                </div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Beta</div>
                    <div class="metric-value">{fmt(data['Beta'])}</div>
                </div>""", unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Debt / Equity</div>
                    <div class="metric-value">{fmt(data['Debt to Equity Ratio'])}</div>
                </div>""", unsafe_allow_html=True)
            with col5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Revenue Growth</div>
                    <div class="metric-value">{fmt(data['Revenue Growth'], suffix="%") if data['Revenue Growth'] else "N/A"}</div>
                </div>""", unsafe_allow_html=True)

            # Price Chart
            if history is not None and not history.empty:
                st.markdown("### 6-Month Price Chart")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history.index,
                    y=history["Close"],
                    mode="lines",
                    name="Close Price",
                    line=dict(color="#4c9be8", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(76, 155, 232, 0.08)"
                ))
                fig.update_layout(
                    paper_bgcolor="#1a1f2e",
                    plot_bgcolor="#1a1f2e",
                    font=dict(color="#7a8fa6"),
                    xaxis=dict(gridcolor="#2e3a52", showgrid=True),
                    yaxis=dict(gridcolor="#2e3a52", showgrid=True, tickprefix="$"),
                    margin=dict(l=0, r=0, t=20, b=0),
                    height=380
                )
                st.plotly_chart(fig, use_container_width=True)

                # Volume Chart
                st.markdown("### Volume")
                fig_vol = go.Figure()
                fig_vol.add_trace(go.Bar(
                    x=history.index,
                    y=history["Volume"],
                    name="Volume",
                    marker_color="rgba(76, 155, 232, 0.5)"
                ))
                fig_vol.update_layout(
                    paper_bgcolor="#1a1f2e",
                    plot_bgcolor="#1a1f2e",
                    font=dict(color="#7a8fa6"),
                    xaxis=dict(gridcolor="#2e3a52"),
                    yaxis=dict(gridcolor="#2e3a52"),
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=220
                )
                st.plotly_chart(fig_vol, use_container_width=True)

        # -----------------------
        # Tab 2: AI Analysis
        # -----------------------
        with tab2:
            with st.spinner("Running AI analysis..."):
                analysis = generate_response(str(user_profile), str(data), ticker)

            if "error" in analysis:
                st.error(analysis["error"])
                if analysis.get("raw_response"):
                    st.text(analysis["raw_response"])
            else:
                recommendation = analysis.get("Recommendation", "N/A")
                badge_class = (
                    "badge-buy" if "buy" in recommendation.lower() else
                    "badge-avoid" if "avoid" in recommendation.lower() else
                    "badge-hold"
                )

                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-label">Recommendation</div>
                    <span class="{badge_class}">{recommendation}</span>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-label">Reasoning</div>
                    <div class="analysis-value">{analysis.get("Reasoning", "N/A")}</div>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-label">Risk Rating</div>
                    <div class="analysis-value">{analysis.get("Risk Rating", "N/A")}</div>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-label">Alignment with Goals</div>
                    <div class="analysis-value">{analysis.get("Alignment with Goals", "N/A")}</div>
                </div>""", unsafe_allow_html=True)

        # -----------------------
        # Tab 3: Follow-up Chat
        # -----------------------
        with tab3:
            st.markdown("### Ask anything about this stock")
            st.caption(f"Currently analyzing: **{ticker}** · Your profile is included as context")

            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            user_question = st.chat_input(f"Ask about {ticker}...")

            if user_question:
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                with st.chat_message("user"):
                    st.markdown(user_question)

                system_msg = {
                    "role": "system",
                    "content": (
                        f"You are an AI investment analyst. The user is asking about {ticker}. "
                        f"Stock data: {json.dumps(data)}. "
                        f"User profile: {json.dumps(user_profile)}. "
                        "Answer clearly and concisely in plain text, no JSON."
                    )
                }
                messages = [system_msg] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            chat_response = client.chat.completions.create(
                                model="gpt-5-mini",
                                messages=messages
                            )
                            reply = chat_response.choices[0].message.content.strip()
                        except Exception as e:
                            reply = f"Error getting response: {e}"
                    st.markdown(reply)

                st.session_state.chat_history.append({"role": "assistant", "content": reply})