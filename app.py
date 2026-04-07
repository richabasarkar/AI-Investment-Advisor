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
# Light Theme CSS
# -----------------------
st.markdown("""
<style>
    /* App background */
    .stApp {
        background-color: #f5f7fb;
        color: #111111;
    }

    /* Header */
    .header-banner {
        background: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 16px;
        padding: 36px 40px;
        margin-bottom: 32px;
    }
    .header-banner h1 {
        color: #111111;
    }
    .header-banner p {
        color: #555;
    }

    /* Cards */
    .metric-card, .analysis-card {
        background-color: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 12px;
        padding: 20px;
    }

    .metric-label, .analysis-label {
        color: #666;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-value {
        color: #111;
        font-size: 1.5rem;
        font-weight: 700;
    }

    .analysis-value {
        color: #222;
        font-size: 1rem;
        line-height: 1.6;
    }

    /* Recommendation badges */
    .badge-buy {
        background-color: #e6f4ea;
        color: #1e7e34;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 600;
    }
    .badge-hold {
        background-color: #fff3cd;
        color: #856404;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 600;
    }
    .badge-avoid {
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 600;
    }

    /* Input */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #111 !important;
        border: 1px solid #ccc !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e6ef;
    }

</style>
""", unsafe_allow_html=True)

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
    <p>Analyze stocks with AI insights tailored to your investment strategy.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------
# Sidebar
# -----------------------
st.sidebar.markdown("## Your Preferences")

risk = st.sidebar.selectbox("Risk", ["Low", "Medium", "High"])
horizon = st.sidebar.selectbox("Horizon", ["Short", "Medium", "Long"])
goal = st.sidebar.selectbox("Goal", ["Growth", "Income", "Preservation"])

user_profile = {
    "risk": risk,
    "horizon": horizon,
    "goal": goal
}

# -----------------------
# Input
# -----------------------
ticker = st.text_input("Enter ticker (AAPL, TSLA)").upper().strip()

# -----------------------
# Data
# -----------------------
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if "currentPrice" not in info:
            return None, None
        data = {
            "Price": info.get("currentPrice"),
            "PE": info.get("trailingPE"),
            "Beta": info.get("beta"),
        }
        history = stock.history(period="6mo")
        return data, history
    except:
        return None, None

# -----------------------
# AI
# -----------------------
def generate_response(profile, data):
    prompt = f"""
User profile: {profile}
Stock data: {data}

Return JSON:
{{
 "Recommendation": "",
 "Reasoning": "",
 "Risk": ""
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)

# -----------------------
# UI
# -----------------------
if ticker:
    data, history = get_stock_data(ticker)

    if data is None:
        st.error("Invalid ticker")
    else:
        col1, col2, col3 = st.columns(3)

        col1.markdown(f"<div class='metric-card'><div class='metric-label'>Price</div><div class='metric-value'>${data['Price']}</div></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='metric-card'><div class='metric-label'>P/E</div><div class='metric-value'>{data['PE']}</div></div>", unsafe_allow_html=True)
        col3.markdown(f"<div class='metric-card'><div class='metric-label'>Beta</div><div class='metric-value'>{data['Beta']}</div></div>", unsafe_allow_html=True)

        if history is not None and not history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history.index, y=history["Close"]))
            fig.update_layout(
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(color="#111")
            )
            st.plotly_chart(fig, use_container_width=True)

        if st.button("Analyze"):
            result = generate_response(user_profile, data)

            rec = result.get("Recommendation", "")
            badge = "badge-buy" if "buy" in rec.lower() else "badge-hold"

            st.markdown(f"<div class='analysis-card'><span class='{badge}'>{rec}</span></div>", unsafe_allow_html=True)
            st.write(result.get("Reasoning"))