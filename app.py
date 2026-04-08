import streamlit as st
import yfinance as yf
from openai import OpenAI
import os
import json
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="AI Investment Advisor", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; color: #111111; }
    .header-banner { background: #ffffff; border: 1px solid #e2e6ef; border-radius: 16px; padding: 36px 40px; margin-bottom: 32px; }
    .header-banner h1 { font-size: 2.4rem; font-weight: 700; color: #111111; }
    .header-banner p { color: #555; }
    .analysis-card { background-color: #ffffff; border: 1px solid #e2e6ef; border-radius: 12px; padding: 24px 28px; margin-bottom: 16px; }
    .analysis-label { font-size: 0.75rem; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .analysis-value { font-size: 1rem; color: #222; line-height: 1.6; }
    .badge-buy { background-color: #e6f4ea; color: #1e7e34; border: 1px solid #1e7e34; border-radius: 8px; padding: 6px 16px; font-weight: 700; font-size: 1.1rem; }
    .badge-avoid { background-color: #f8d7da; color: #721c24; border: 1px solid #721c24; border-radius: 8px; padding: 6px 16px; font-weight: 700; font-size: 1.1rem; }
    .badge-hold { background-color: #fff3cd; color: #856404; border: 1px solid #856404; border-radius: 8px; padding: 6px 16px; font-weight: 700; font-size: 1.1rem; }
    .stTabs [data-baseweb="tab-list"] { display: flex; justify-content: center; gap: 20px; background-color: #ffffff; border-radius: 14px; padding: 10px; border: 1px solid #e2e6ef; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f3f8; color: #444; border-radius: 10px; padding: 10px 24px; font-weight: 600; transition: all 0.2s ease; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #e4e8f2; color: #000; }
    .stTabs [aria-selected="true"] { background-color: #dfe6f3 !important; color: #000 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
    .stTextInput > div > div > input { background-color: #ffffff; border: 1px solid #ccc; color: #111111; border-radius: 10px; padding: 12px 16px; font-size: 1rem; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e6ef; }
    hr { border-color: #e2e6ef; }
    [data-testid="stChatMessage"] { background-color: #ffffff; border: 1px solid #e2e6ef; border-radius: 12px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.markdown("""
<div class="header-banner">
    <h1>📈 AI Investment Advisor</h1>
    <p>Enter a stock ticker to get real-time data, AI-powered analysis, and personalized insights based on your investment profile.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------
# Sidebar
# -----------------------
st.sidebar.markdown("## Your Preferences")
risk = st.sidebar.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
horizon = st.sidebar.selectbox("Investment Horizon", ["Short", "Medium", "Long"])
goal = st.sidebar.selectbox("Investment Goal", ["Growth", "Stable Income", "Capital Preservation"])
sector = st.sidebar.multiselect("Preferred Sectors", ["Technology", "Healthcare", "Finance", "Energy", "Consumer Goods"])
investment_type = st.sidebar.selectbox("Investment Type", ["Stocks", "ETFs", "Bonds", "Debt Financing", "Options"])
option_types = []
if investment_type == "Options":
    option_types = st.sidebar.multiselect("Option Type(s)", ["Call", "Put", "Future", "Other"])

# -----------------------
# Ticker input — Enter key supported via st.form
# -----------------------
with st.form(key="ticker_form"):
    ticker_col, btn_col = st.columns([5, 1])
    with ticker_col:
        ticker_input = st.text_input("🔍 Enter a stock ticker (e.g., AAPL, TSLA, MSFT)",
                                     value=st.session_state.get("ticker_input", ""),
                                     label_visibility="visible")
    with btn_col:
        st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)
        analyse_clicked = st.form_submit_button("Analyse", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

ticker = ticker_input.upper().strip() if ticker_input else ""

if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ticker
    st.session_state.chat_history = []
    st.session_state.active_tab = 0
    st.session_state.rec_analysis_cache = {}
else:
    if ticker and analyse_clicked:
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
        name = info.get("shortName") or info.get("longName") or ticker
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            try:
                dl = yf.download(ticker, period="1d", interval="1m", progress=False)
                if not dl.empty:
                    price = round(float(dl["Close"].iloc[-1]), 2)
            except Exception:
                price = None
        pe = info.get("trailingPE") or info.get("forwardPE")
        beta = info.get("beta")
        de_ratio = info.get("debtToEquity")
        rev_growth = info.get("revenueGrowth")
        def fmt(val, pct=False):
            if val is None: return "N/A"
            if pct: return f"{round(val * 100, 2)}%"
            return round(val, 2)
        metrics = {"Company": name, "Price": fmt(price), "P/E": fmt(pe), "Beta": fmt(beta),
                   "Debt/Equity": fmt(de_ratio), "Revenue Growth": fmt(rev_growth, pct=True)}
        try:
            history = stock.history(period="6mo")
            if history.empty: history = None
        except Exception:
            history = None
        return metrics, history
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return {}, None


@st.cache_data(ttl=300)
def get_extended_fundamentals(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        def safe(key, pct=False):
            v = info.get(key)
            if v is None: return "N/A"
            if pct: return f"{round(v * 100, 2)}%"
            return round(v, 2)
        return {
            "Ticker": ticker.upper(),
            "P/E (TTM)": safe("trailingPE"),
            "Forward P/E": safe("forwardPE"),
            "P/S": safe("priceToSalesTrailing12Months"),
            "P/B": safe("priceToBook"),
            "EV/EBITDA": safe("enterpriseToEbitda"),
            "Debt/Equity": safe("debtToEquity"),
            "ROE": safe("returnOnEquity", pct=True),
            "Gross Margin": safe("grossMargins", pct=True),
            "Net Margin": safe("profitMargins", pct=True),
            "Rev Growth (YoY)": safe("revenueGrowth", pct=True),
            "Dividend Yield": safe("dividendYield", pct=True),
        }
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def get_competitors(ticker):
    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": (
                f"List the 4 most direct publicly traded competitors of {ticker} (stock ticker). "
                "Return ONLY a JSON array of ticker symbols, e.g. [\"AAPL\",\"MSFT\"]. No explanation, no markdown."
            )}]
        )
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        competitors = json.loads(raw)
        return [c.upper() for c in competitors if isinstance(c, str)]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def generate_recommendations(risk, horizon, goal, sectors, investment_type, option_types=[]):
    type_instructions = {
        "Stocks": "Recommend individual stocks (equities) only. Use standard stock tickers (e.g. AAPL, MSFT).",
        "ETFs": "Recommend ETFs only. Use ETF tickers (e.g. VOO, QQQ, ARKK, XLK). Do NOT recommend individual stocks.",
        "Bonds": "Recommend bond ETFs or bond funds only (e.g. BND, TLT, AGG, GOVT, HYG).",
        "Debt Financing": "Recommend fixed-income instruments and debt-focused funds only (e.g. BND, LQD, BIZD, ARCC).",
        "Options": f"Recommend options. Focus on types: {', '.join(option_types) if option_types else 'any'}."
    }
    sector_note = f"Focus on these sectors: {', '.join(sectors)}." if sectors else "No specific sector preference — diversify."
    risk_guidance = {"Low": "Prioritize capital preservation.", "Medium": "Balance growth and stability.", "High": "Prioritize high growth potential."}
    horizon_guidance = {"Short": "Under 1 year.", "Medium": "1–5 years.", "Long": "5+ years, growth-oriented."}
    goal_guidance = {"Growth": "Capital appreciation.", "Stable Income": "Dividends or interest income.", "Capital Preservation": "Protect principal."}
    prompt = f"""You are an expert financial advisor helping a beginner investor.

USER PROFILE:
- Investment Type: {investment_type}
- Option Type(s): {', '.join(option_types) if option_types else 'N/A'}
- Risk Tolerance: {risk} — {risk_guidance.get(risk,'')}
- Investment Horizon: {horizon} — {horizon_guidance.get(horizon,'')}
- Investment Goal: {goal} — {goal_guidance.get(goal,'')}
- Sector Preference: {sector_note}

STRICT RULES:
1. {type_instructions.get(investment_type,'')}
2. Recommend exactly 5 options. Only Buy or Hold verdicts.
3. Return ONLY valid JSON array, no markdown.

FORMAT:
[{{"ticker":"X","company":"Full Name","reason":"One sentence.","recommendation":"Buy","reasoning":"Detail.","risk_rating":"Low","alignment":"Goal alignment."}}]"""
    try:
        response = client.chat.completions.create(model="gpt-5-mini", messages=[{"role": "user", "content": prompt}])
        text_response = response.choices[0].message.content.strip()
        if text_response.startswith("```"):
            text_response = text_response.split("```")[1]
            if text_response.startswith("json"): text_response = text_response[4:]
        return json.loads(text_response.strip())
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600)
def generate_single_analysis(ticker, risk, horizon, goal, sectors, investment_type, option_types=[]):
    sector_note = f"Focus on these sectors: {', '.join(sectors)}." if sectors else "No specific sector preference."
    prompt = f"""You are an expert financial advisor. Analyse "{ticker}" for this user.

USER PROFILE:
- Risk: {risk}, Horizon: {horizon}, Goal: {goal}
- Investment Type: {investment_type}, Sectors: {sector_note}

Return ONLY a valid JSON object, no markdown.
FORMAT: {{"Recommendation":"Buy/Hold/Avoid","Reasoning":"Detail.","Risk Rating":"Low/Medium/High","Alignment with Goals":"Detail."}}"""
    try:
        response = client.chat.completions.create(model="gpt-5-mini", messages=[{"role": "user", "content": prompt}])
        text_response = response.choices[0].message.content.strip()
        if text_response.startswith("```"):
            text_response = text_response.split("```")[1]
            if text_response.startswith("json"): text_response = text_response[4:]
        return json.loads(text_response.strip())
    except Exception as e:
        return {"error": str(e)}


def generate_news_report(ticker):
    """Comprehensive news report using GPT-5-mini with web search."""
    prompt = f"""You are a financial journalist writing for a general audience — assume the reader has NO finance background.

Use your web search capability to find the latest news, filings, and financial data for stock ticker: {ticker}

Write a comprehensive report using these clearly labelled sections:

**Quick Summary**
In 3-5 bullet points, give the most important things to know about this company right now. Keep it very plain and simple.

**1. Company Overview**
What does this company do in plain English? What products/services do they sell and who are their customers?

**2. Recent News (Last 1-3 Months)**
Search for and summarise the most important recent news stories. For each story, explain in simple terms why it matters to someone who owns or is considering buying this stock.

**3. Latest Earnings Report**
Search for the most recent quarterly earnings. Did they beat or miss expectations? Use simple language. Include key numbers: revenue, profit, EPS. Explain what these numbers mean for ordinary investors.

**4. SEC Filings and Financial Trends**
Summarise any notable recent SEC filings (10-K, 10-Q, 8-K). What do the financial trends show — is revenue growing, are profits improving, is debt increasing? Explain in simple terms what these trends mean.

**5. Industry Health**
How is the broader industry doing? Is the sector growing, struggling, or facing headwinds? What macro trends are relevant?

**6. Analyst Sentiment**
What are analysts saying? What is the general consensus (buy/hold/sell)? Any notable price target changes?

**7. Key Risks**
What are the 3-4 biggest risks to this stock right now, explained in plain English?

Be thorough, use plain language throughout, and aim for 700-1000 words total. Always search for the latest available data before writing."""
    try:
        # Use gpt-4o-search-preview with web_search_options for live web access
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            web_search_options={"search_context_size": "high"},
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback: gpt-5-mini without live search
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1500
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            return f"Error generating news report: {str(e2)}"


def generate_dcf(ticker):
    """Full DCF model using GPT-5-mini with web search."""
    prompt = f"""You are a financial analyst building a Discounted Cash Flow (DCF) valuation for {ticker}.

CRITICAL INSTRUCTIONS:
- Use your web search tool NOW to find the most recent 10-K, earnings releases, and investor relations data for {ticker}.
- Do NOT ask the user for any input or present multiple options. Always proceed immediately and complete the full DCF model yourself in one response.
- If some data points are uncertain or estimated, clearly label them as [Estimated] but still provide a number and keep going.
- Never stop mid-analysis to ask a question. Complete the entire model from start to finish.

Structure your report with these sections:

**1. Historical Financials (Last 3 Years)**
Search for and summarise real revenue, operating income, free cash flow, and capex figures for the last 3 fiscal years. Label any estimated numbers as [Estimated].

**2. DCF Assumptions**
State and justify all assumptions: revenue growth rate (years 1-5 and terminal), EBIT margin, tax rate, D&A, capex, working capital changes, WACC (explain what this means in one simple sentence), terminal growth rate.

**3. Projected Free Cash Flows (5 Years)**
Show a year-by-year table of projected free cash flow based on your assumptions.

**4. Terminal Value**
Calculate terminal value using the Gordon Growth Model. Explain in one sentence what this means for a non-finance reader.

**5. DCF Valuation**
Sum of PV of FCFs + PV of Terminal Value = Enterprise Value. Subtract net debt to get Equity Value. Divide by diluted shares outstanding = Implied Share Price. Show every step clearly.

**6. Sensitivity Analysis**
Show a simple table of implied share prices under different combinations of WACC and terminal growth rate.

**7. Verdict**
Compare the DCF implied price to the current market price. Is the stock undervalued, fairly valued, or overvalued? Explain simply in 2-3 sentences.

Write everything in plain English so a non-finance reader can follow along. Complete the full analysis without asking any questions."""
    try:
        # Use gpt-4o-search-preview with web_search_options for live web access
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            web_search_options={"search_context_size": "high"},
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback: gpt-5-mini without live search
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            return f"Error generating DCF: {str(e2)}"


# -----------------------
# Tabs — all 6
# -----------------------
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Recommendations", "Stock Data", "AI Analysis", "News", "Comparison & DCF", "Chat"
])

# -----------------------
# Tab 0 — Recommendations
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
                if st.button("Select", key=f"rec_{i}"):
                    st.session_state.last_ticker = ticker_symbol
                    st.session_state.ticker_input = ticker_symbol
                    st.session_state.chat_history = []
                    st.rerun()
            st.markdown("<hr style='margin: 6px 0; border-color:#e2e6ef;'>", unsafe_allow_html=True)

# -----------------------
# Tab 1 — Stock Data
# -----------------------
with tab1:
    current_ticker = st.session_state.last_ticker
    if current_ticker:
        data, history = get_stock_data(current_ticker)
        if not data:
            st.error(f"No data found for {current_ticker}. Make sure the ticker is valid.")
        else:
            st.markdown(f"### 📈 Data for {current_ticker}")
            metric_keys = list(data.keys())
            cols = st.columns(len(metric_keys))
            for j, key in enumerate(metric_keys):
                cols[j].metric(label=key, value=data[key])
            if history is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close"))
                fig.update_layout(title=f"{current_ticker} 6-Month Price History", xaxis_title="Date",
                                  yaxis_title="Price ($)", paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                                  font=dict(color="#111111"), height=450)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No historical data available for chart.")

# -----------------------
# Tab 2 — AI Analysis (no Refresh button)
# -----------------------
with tab2:
    if st.session_state.last_ticker:
        current_ticker = st.session_state.last_ticker
        cached_analysis = st.session_state.rec_analysis_cache.get(current_ticker)
        if cached_analysis:
            st.markdown(f"### Analysis for {current_ticker}")
            st.caption("Analysis generated based on your investment profile.")
            verdict = cached_analysis.get("Recommendation", "Hold")
            badge_class = {"Buy": "badge-buy", "Hold": "badge-hold", "Avoid": "badge-avoid"}.get(verdict, "badge-hold")
            st.markdown(f'<span class="{badge_class}">{verdict}</span>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(f"""
            <div class="analysis-card"><div class="analysis-label">Reasoning</div><div class="analysis-value">{cached_analysis.get("Reasoning","N/A")}</div></div>
            <div class="analysis-card"><div class="analysis-label">Risk Rating</div><div class="analysis-value">{cached_analysis.get("Risk Rating","N/A")}</div></div>
            <div class="analysis-card"><div class="analysis-label">Alignment with Goals</div><div class="analysis-value">{cached_analysis.get("Alignment with Goals","N/A")}</div></div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"### Analysis for {current_ticker}")
            if st.button("🧠 Generate Analysis", key="generate_analysis_btn"):
                with st.spinner(f"Analysing {current_ticker}..."):
                    generated = generate_single_analysis(current_ticker, risk, horizon, goal,
                                                         tuple(sector), investment_type, option_types)
                if isinstance(generated, dict) and "error" in generated:
                    st.error(f"Could not generate analysis: {generated['error']}")
                else:
                    st.session_state.rec_analysis_cache[current_ticker] = generated
                    st.rerun()

# -----------------------
# Tab 3 — News
# -----------------------
with tab3:
    current_ticker = st.session_state.last_ticker
    if not current_ticker:
        st.info("Enter a stock ticker above and click Analyse to load news.")
    else:
        st.markdown(f"### 📰 News & Reports — {current_ticker}")
        st.caption("Powered by AI web search · Updated on demand")
        news_cache_key = f"news_{current_ticker}"
        if st.button("🔍 Load / Refresh News", key="load_news_btn", use_container_width=False):
            with st.spinner("🔍 Searching the web for latest news, earnings, and industry reports..."):
                report = generate_news_report(current_ticker)
            st.session_state[news_cache_key] = report
        if news_cache_key in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state[news_cache_key])
            st.markdown("---")
            st.markdown("#### 🔗 Find Official Reports")
            st.markdown(
                f"- [SEC Filings (EDGAR)](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={current_ticker}&type=10-K&dateb=&owner=include&count=10) — Annual (10-K) and Quarterly (10-Q) reports\n"
                f"- [Macrotrends Financials](https://www.macrotrends.net/stocks/research?search={current_ticker}) — Income statement, balance sheet, cash flow\n"
                f"- [Yahoo Finance](https://finance.yahoo.com/quote/{current_ticker}/financials/) — Earnings and financials\n"
                f"- [Seeking Alpha](https://seekingalpha.com/symbol/{current_ticker}/earnings) — Earnings coverage and analysis"
            )
        else:
            st.info("Click **Load / Refresh News** to fetch the latest report for this stock.")

# -----------------------
# Tab 4 — Comparison & DCF
# -----------------------
with tab4:
    current_ticker = st.session_state.last_ticker
    if not current_ticker:
        st.info("Enter a stock ticker above and click Analyse to load comparison data.")
    else:
        st.markdown(f"### 📊 Peer Comparison — {current_ticker} vs Competitors & S&P 500")

        comp_cache_key = f"comp_{current_ticker}"
        if comp_cache_key not in st.session_state:
            with st.spinner("Identifying competitors..."):
                competitors = get_competitors(current_ticker)
            st.session_state[comp_cache_key] = competitors
        else:
            competitors = st.session_state[comp_cache_key]

        all_tickers = [current_ticker] + competitors + ["SPY"]

        fund_cache_key = f"fund_{current_ticker}"
        if fund_cache_key not in st.session_state:
            with st.spinner("Loading peer fundamentals..."):
                all_fundamentals = [fd for t in all_tickers if (fd := get_extended_fundamentals(t))]
            st.session_state[fund_cache_key] = all_fundamentals
        else:
            all_fundamentals = st.session_state[fund_cache_key]

        if all_fundamentals:
            df = pd.DataFrame(all_fundamentals).set_index("Ticker")

            def highlight_main(row):
                if row.name == current_ticker.upper():
                    return ["background-color: #eef3ff; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.markdown("##### Key Ratios at a Glance")
            st.caption(f"Row highlighted in blue = **{current_ticker}** · SPY = S&P 500 benchmark proxy")
            st.dataframe(df.style.apply(highlight_main, axis=1), use_container_width=True)

            # P/E bar chart
            pe_vals = {row["Ticker"]: float(row["P/E (TTM)"]) for row in all_fundamentals
                       if row.get("P/E (TTM)") != "N/A" and row.get("P/E (TTM)") is not None
                       and str(row.get("P/E (TTM)","")).replace(".","").lstrip("-").isdigit() or
                       (lambda v: v != "N/A" and v is not None and str(v).replace(".","").lstrip("-").replace("e","").replace("+","").isdigit())(row.get("P/E (TTM)"))}
            # simpler approach
            pe_vals = {}
            for row in all_fundamentals:
                t = row.get("Ticker")
                v = row.get("P/E (TTM)")
                try:
                    if v != "N/A" and v is not None:
                        pe_vals[t] = float(v)
                except (ValueError, TypeError):
                    pass

            if pe_vals:
                colors = ["#3a5bb5" if t == current_ticker.upper() else "#b0bfe8" for t in pe_vals]
                fig_pe = go.Figure(go.Bar(x=list(pe_vals.keys()), y=list(pe_vals.values()),
                                          marker_color=colors, text=[str(v) for v in pe_vals.values()], textposition="outside"))
                fig_pe.update_layout(title="P/E Ratio Comparison", yaxis_title="P/E (TTM)",
                                     paper_bgcolor="#ffffff", plot_bgcolor="#f5f7fb",
                                     font=dict(color="#111"), height=360, showlegend=False)
                st.plotly_chart(fig_pe, use_container_width=True)

            # Net Margin bar chart
            margin_vals = {}
            for row in all_fundamentals:
                t = row.get("Ticker")
                m = row.get("Net Margin")
                try:
                    if m != "N/A" and m is not None and "%" in str(m):
                        margin_vals[t] = float(str(m).replace("%", ""))
                except (ValueError, TypeError):
                    pass

            if margin_vals:
                colors2 = ["#1e7e34" if t == current_ticker.upper() else "#a8d5b0" for t in margin_vals]
                fig_margin = go.Figure(go.Bar(x=list(margin_vals.keys()), y=list(margin_vals.values()),
                                              marker_color=colors2, text=[f"{v}%" for v in margin_vals.values()], textposition="outside"))
                fig_margin.update_layout(title="Net Margin Comparison (%)", yaxis_title="Net Margin (%)",
                                         paper_bgcolor="#ffffff", plot_bgcolor="#f5f7fb",
                                         font=dict(color="#111"), height=360, showlegend=False)
                st.plotly_chart(fig_margin, use_container_width=True)
        else:
            st.warning("Could not load peer comparison data.")

        # DCF Section
        st.markdown("---")
        st.markdown("### 🧮 DCF Valuation Model")
        st.caption("A Discounted Cash Flow (DCF) model estimates what a company is *worth today* based on the cash it's expected to generate in the future. Click below to generate one.")
        dcf_cache_key = f"dcf_{current_ticker}"
        if st.button("📐 Create DCF Model", key="dcf_btn"):
            with st.spinner("🔍 Fetching financials and building DCF model — this may take 30–60 seconds..."):
                dcf_result = generate_dcf(current_ticker)
            st.session_state[dcf_cache_key] = dcf_result
        if dcf_cache_key in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state[dcf_cache_key])

# -----------------------
# Tab 5 — Chat (Enter key supported via st.form)
# -----------------------
with tab5:
    st.markdown("### 💬 Ask About This Investment")
    current_ticker = st.session_state.last_ticker

    def build_chat_context(ticker):
        context_parts = []
        if ticker:
            context_parts.append(f"The user is currently viewing the stock ticker: {ticker}.")
            stock_data, _ = get_stock_data(ticker)
            if stock_data:
                context_parts.append(f"Live stock data for {ticker} — {', '.join(f'{k}: {v}' for k, v in stock_data.items())}.")
            analysis = st.session_state.rec_analysis_cache.get(ticker)
            if analysis:
                context_parts.append(
                    f"AI analysis for {ticker}: Recommendation: {analysis.get('Recommendation','N/A')}. "
                    f"Reasoning: {analysis.get('Reasoning','N/A')}. "
                    f"Risk Rating: {analysis.get('Risk Rating','N/A')}. "
                    f"Alignment with Goals: {analysis.get('Alignment with Goals','N/A')}."
                )
        context_parts.append(
            f"User investment profile — Risk Tolerance: {risk}, Horizon: {horizon}, Goal: {goal}, "
            f"Investment Type: {investment_type}, Preferred Sectors: {', '.join(sector) if sector else 'None specified'}."
        )
        return " ".join(context_parts)

    with st.form(key="chat_form", clear_on_submit=True):
        chat_col, send_col = st.columns([5, 1])
        with chat_col:
            chat_input = st.text_input("Ask a question about this investment...", key="chat_input")
        with send_col:
            st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)
            send_clicked = st.form_submit_button("Send", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    if send_clicked and chat_input:
        st.session_state.chat_history.append({"role": "user", "content": chat_input})
        context = build_chat_context(current_ticker)
        system_prompt = (
            "You are an expert AI financial analyst and investment advisor with deep knowledge of "
            "equity markets, macroeconomics, company fundamentals, and investment strategy. "
            "Give thorough, insightful, well-structured answers — like consulting a senior financial analyst. "
            "Draw on the context provided AND your broader knowledge of the company, sector, competitive landscape, "
            "recent news, earnings history, and analyst sentiment. "
            "Use bullet points or numbered lists where appropriate. Be honest about risks. "
            "Tailor answers to the user's investment profile. Do not give vague answers.\n\n"
            f"CONTEXT:\n{context}"
        )
        messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history
        with st.spinner("🤔 AI is thinking..."):
            try:
                resp = client.chat.completions.create(model="gpt-5-mini", messages=messages, max_completion_tokens=1000, temperature=0.7)
                st.session_state.chat_history.append({"role": "assistant", "content": resp.choices[0].message.content})
            except Exception as e:
                st.error(f"Error generating response: {e}")
        st.rerun()

    for chat in reversed(st.session_state.chat_history):
        if chat["role"] == "user":
            st.markdown(f"**You:** {chat['content']}")
        else:
            st.markdown(f"**AI:** {chat['content']}")