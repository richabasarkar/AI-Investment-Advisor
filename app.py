import streamlit as st
import yfinance as yf
from openai import OpenAI
import os
import json
import time

# -----------------------
# Initialize OpenAI client
# -----------------------
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
# Helper Functions
# -----------------------
def fetch_stock_data(ticker, retries=2):
    """Fetch stock data robustly with retries."""
    ticker = ticker.upper().strip()
    for attempt in range(retries + 1):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # Check critical fields
            if "regularMarketPrice" in info:
                return {
                    "Price": info.get("currentPrice"),
                    "Price to Earnings Ratio": info.get("trailingPE"),
                    "Beta": info.get("beta"),
                    "Debt to Equity Ratio": info.get("debtToEquity"),
                    "Revenue Growth": info.get("revenueGrowth")
                }
        except Exception:
            pass
        time.sleep(1)
    return None

def generate_response(profile, data, ticker):
    """Call OpenAI to get structured AI analysis."""
    prompt = f"""
You are an AI investment analyst. User wants personalized advice.

User Profile:
{profile}

Stock Data:
{data}

Return a structured JSON response like this:
{{
  "recommendation": "Buy / Hold / Avoid",
  "reasoning": "Explain why this stock fits the user profile",
  "risk_rating": "Low / Medium / High",
  "alignment": "How well it matches user's goal, risk, horizon, and investment type"
}}

Prioritize:
- Low-risk options for users with Low risk tolerance
- Debt financing options if user selected Debt Financing
- Long-term growth if user horizon is Long
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        text_response = response.choices[0].message.content
        # Parse JSON
        analysis = json.loads(text_response)
        # Format string fields in uppercase
        for key, value in analysis.items():
            if isinstance(value, str):
                analysis[key] = value.upper()
        return analysis
    except Exception as e:
        return {"error": f"AI response error: {e}", "raw_response": text_response if 'text_response' in locals() else None}

# -----------------------
# Main UI
# -----------------------
ticker_input = st.text_input("Enter a stock ticker (e.g., AAPL)")

if ticker_input:
    data = fetch_stock_data(ticker_input)
    if data is None:
        st.error(f"No valid data found for {ticker_input.upper()}")
    else:
        st.subheader("Stock Data")
        st.json(data)
        if st.button("Analyze"):
            with st.spinner("Analyzing stock with AI..."):
                analysis = generate_response(user_profile, data, ticker_input)
                st.subheader("AI Analysis")
                st.json(analysis)