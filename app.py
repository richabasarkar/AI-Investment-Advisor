import streamlit as st
import yfinance as yf
from openai import OpenAI
import os
import json

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("AI Investment Advisor")

# -----------------------
# Sidebar Inputs
# -----------------------
st.sidebar.header("Your Preferences")

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
ticker_input = st.text_input("Enter a stock ticker (e.g., AAPL)")
ticker = ticker_input.upper() if ticker_input else ""

# -----------------------
# Caching stock data and AI analysis
# -----------------------
@st.cache_data
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if "currentPrice" not in info:
            return None
        return {
            "Price": info.get("currentPrice"),
            "Price to Earnings Ratio": info.get("trailingPE"),
            "Beta": info.get("beta"),
            "Debt to Equity Ratio": info.get("debtToEquity"),
            "Revenue Growth": info.get("revenueGrowth")
        }
    except:
        return None

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
            model="gpt-5-mini",  # ✅ Valid API model
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content.strip()
        
        if not text_response:
            return {"error": "AI returned empty response", "raw_response": None}

        # Parse JSON
        try:
            return json.loads(text_response)
        except json.JSONDecodeError:
            return {"error": "AI returned invalid JSON", "raw_response": text_response}

    except Exception as e:
        return {"error": f"AI response error: {e}", "raw_response": None}

# -----------------------
# Show stock data and analysis
# -----------------------
if ticker:
    data = get_stock_data(ticker)
    if data is None:
        st.error(f"No valid data found for {ticker}")
    else:
        st.subheader("Stock Data")
        st.write(data)
        if st.button("Analyze"):
            analysis = generate_response(user_profile, data, ticker)
            st.subheader("AI Analysis")
            st.json(analysis)