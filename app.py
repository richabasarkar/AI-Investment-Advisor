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

# Reset chat history if ticker changes
if "last_ticker" not in st.session_state or st.session_state.last_ticker != ticker:
    st.session_state.chat_history = []
    st.session_state.last_ticker = ticker

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
# Show stock data and analysis
# -----------------------
if ticker:
    data = get_stock_data(ticker)
    if data is None:
        st.error(f"No valid data found for {ticker}")
    else:
        st.subheader("Stock Data")
        st.markdown(f"**Price:** {data.get('Price', 'N/A')}")
        st.markdown(f"**Price to Earnings Ratio:** {data.get('Price to Earnings Ratio', 'N/A')}")
        st.markdown(f"**Beta:** {data.get('Beta', 'N/A')}")
        st.markdown(f"**Debt to Equity Ratio:** {data.get('Debt to Equity Ratio', 'N/A')}")
        st.markdown(f"**Revenue Growth:** {data.get('Revenue Growth', 'N/A')}")

        with st.spinner("Analyzing..."):
            analysis = generate_response(user_profile, data, ticker)

        st.subheader("AI Analysis")
        if "error" in analysis:
            st.error(analysis["error"])
            if analysis.get("raw_response"):
                st.text(analysis["raw_response"])
        else:
            st.markdown(f"**Recommendation:** {analysis.get('Recommendation', 'N/A')}")
            st.markdown(f"**Reasoning:** {analysis.get('Reasoning', 'N/A')}")
            st.markdown(f"**Risk Rating:** {analysis.get('Risk Rating', 'N/A')}")
            st.markdown(f"**Alignment with Goals:** {analysis.get('Alignment with Goals', 'N/A')}")

        # -----------------------
        # Follow-up Chat
        # -----------------------
        st.divider()
        st.subheader("Ask a Follow-up Question")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_question = st.chat_input("Ask anything about this stock...")

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

            try:
                chat_response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=messages
                )
                reply = chat_response.choices[0].message.content.strip()
            except Exception as e:
                reply = f"Error getting response: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)