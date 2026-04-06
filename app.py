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
ticker = st.text_input("Enter a stock ticker (e.g., AAPL)")

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "price": info.get("currentPrice"),
            "pe": info.get("trailingPE"),
            "beta": info.get("beta"),
            "debt_to_equity": info.get("debtToEquity"),
            "revenue_growth": info.get("revenueGrowth")
        }
    except:
        return None

def generate_response(profile, data, ticker):
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
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        text_response = response.choices[0].message.content
        return json.loads(text_response)
    except:
        # fallback if JSON fails
        return {"error": "Could not parse AI response", "raw_response": text_response}

if ticker:
    data = get_stock_data(ticker)
    if data is None:
        st.error("Invalid ticker or no data found.")
    else:
        st.subheader("Stock Data")
        st.write(data)
        if st.button("Analyze"):
            analysis = generate_response(user_profile, data, ticker)
            st.subheader("AI Analysis")
            st.json(analysis)