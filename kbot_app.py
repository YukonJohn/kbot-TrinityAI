import streamlit as st
import yfinance as yf
import pandas as pd
import time
from google import genai
from streamlit_gsheets import GSheetsConnection

# ====================== CONFIG & SECURITY ======================
st.set_page_config(page_title="TrinityAI Master Controller", layout="wide")

# PASSWORD PROTECTION
password_guess = st.sidebar.text_input("Unlock TrinityAI:", type="password")
if password_guess != "Trinity":
    st.info("Enter password (Trinity) in sidebar to begin.")
    st.stop()

# --- SECURE CREDENTIALS ---
try:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
    MY_SPREADSHEET = st.secrets["spreadsheet"]
except Exception as e:
    st.error("Missing Secrets: Ensure .streamlit/secrets.toml is configured.")
    st.stop()

# Initialize Gemini AI
client = genai.Client(api_key=MY_API_KEY)

# Initialize Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ====================== AI & SCORING LOGIC ======================
def get_stock_description(ticker):
    try:
        prompt = (f"Act as a professional commodities and stock market analyst in 2026. "
                  f"Give a deep, strategic analysis of the ticker {ticker}. "
                  f"Explain what it is (stock, metal, futures, etc.), current market conditions, "
                  f"key drivers, recent performance, and outlook for the rest of 2026. "
                  f"Keep it professional and useful for a trader. Use 5-6 clear sentences.")
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"TrinityAI SYSTEM ERROR: {e}"

def get_kbot_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if len(hist) < 20: 
            return None
        price = hist['Close'].iloc[-1]
        ema20 = hist['Close'].ewm(span=20).mean().iloc[-1]
        vol_avg = hist['Volume'].tail(20).mean()
        curr_vol = hist['Volume'].iloc[-1]
        score = 0
        if price > ema20: score += 40
        if curr_vol > vol_avg * 1.5: score += 30
        if price > hist['High'].iloc[-5]: score += 30
        return {"Ticker": ticker, "Price": round(price, 2), "Score": int(score)}
    except: 
        return None

# --- NEW FUNCTION: ANOMALY SCANNER ---
def run_anomaly_scanner(tickers):
    st.subheader("📡 TrinityAI Quant Scanner (2-Sigma)")
    st.write("Scanning for mathematical anomalies: High volume + extreme price deviation.")
    
    with st.spinner('Crunching market data...'):
        results = []
        for ticker in tickers:
            try:
                data = yf.Ticker(ticker).history(period="3mo")
                if data.empty or len(data) < 20:
                    continue
                
                data['SMA_20'] = data['Close'].rolling(window=20).mean()
                data['STD_20'] = data['Close'].rolling(window=20).std()
                data['Upper_Limit'] = data['SMA_20'] + (2 * data['STD_20'])
                data['Lower_Limit'] = data['SMA_20'] - (2 * data['STD_20'])
                data['Vol_SMA_20'] = data['Volume'].rolling(window=20).mean()
                
                today = data.iloc[-1]
                
                is_breaking_up = today['Close'] > today['Upper_Limit']
                is_breaking_down = today['Close'] < today['Lower_Limit']
                is_vol_spike = today['Volume'] > (1.5 * today['Vol_SMA_20'])
                
                if (is_breaking_up or is_breaking_down) and is_vol_spike:
                    status = "🚀 Upside Breakout" if is_breaking_up else "🩸 Downside Dump"
                    results.append({
                        "Ticker": ticker,
                        "Signal": status,
                        "Price": f"${today['Close']:.2f}",
                        "Normal Avg": f"${today['SMA_20']:.2f}",
                        "Vol Spike": f"{(today['Volume'] / today['Vol_SMA_20']):.1f}x Normal"
                    })
            except Exception:
                continue
                
        if results:
            st.success(f"Anomaly Detected! Found {len(results)} out-of-bounds assets.")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.info("Market is quiet. All scanned assets are trading within normal mathematical parameters.")

# ====================== INTERFACE ======================
st.title("🤖 Kbot: TrinityAI Master Controller")

# I added the 9th tab here ("💎 Hidden Gems")
tabs = st.tabs(["📊 Analyzer", "🚀 Trends", "🌍 Global Pulse", "⛏️ Mining Scanner", 
                "📁 My Portfolio", "🏆 Top 10", "📈 ETF Explorer", "🚨 Anomaly Scanner", "💎 Hidden Gems"])

# --- TAB 1: ANALYZER ---
with tabs[0]:
    st.header("Stock & Metal Analyzer")
    t_input = st.text_input("Enter Ticker(s) (e.g., SI=F, TSLA):", "SI=F")
    if st.button("Analyze Selected Stocks"):
        tickers = [t.strip().upper() for t in t_input.split(",") if t.strip()]
        for ticker in tickers:
            st.divider()
            st.subheader(f"Strategic Analysis: {ticker}")
            with st.spinner(f"Requesting deep briefing for {ticker}..."):
                st.info(get_stock_description(ticker))
            time.sleep(1.5)
            data = yf.Ticker(ticker).history(period="6mo")
            if not data.empty:
                st.line_chart(data['Close'])
                res = get_kbot_score(ticker)
                if res:
                    st.metric(f"{ticker} Momentum Score", f"{res['Score']}/100")

# --- TAB 2: TRENDS ---
with tabs[1]:
    st.header("Live Market Momentum")
    if st.button("Update Market Momentum"):
        watch = {"S&P 500": "^GSPC", "Gold": "GC=F", "Silver": "SI=F", "Bitcoin": "BTC-USD"}
        cols = st.columns(4)
        for i, (name, sym) in enumerate(watch.items()):
            time.sleep(1)
            p = yf.Ticker(sym).history(period="1d")['Close'].iloc[-1]
            cols[i].metric(name, f"${p:,.2f}")
        
        st.divider()
        with st.spinner("TrinityAI fetching consolidated market briefing..."):
            try:
                asset_list = ", ".join(watch.keys())
                prompt = f"Provide a brief one-sentence strategic summary for each of these: {asset_list}."
                response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.subheader("Strategic Market Briefing")
                st.info(response.text)
            except Exception as e:
                st.error(f"TrinityAI SYSTEM ERROR: {e}")

# --- TAB 3: GLOBAL PULSE ---
with tabs[2]:
    st.header("Gemini AI Analysis")
    if st.button("Generate AI Market Report"):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents="Summarize the current market outlook for Silver.")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"TrinityAI SYSTEM ERROR: {e}")

# --- TAB 4: MINING SCANNER ---
with tabs[3]:
    st.header("⛏️ Sector Scan")
    miners = ["PAAS", "AG", "NEM", "GOLD", "WPM"]
    if st.button("Run Sector Scan"):
        results = [get_kbot_score(m) for m in miners]
        st.table(pd.DataFrame([r for r in results if r]))

# --- TAB 5: MY PORTFOLIO ---
with tabs[4]:
    st.header("📁 TrinityAI Portfolio Command")
    
    with st.expander("➕ Add New Holdings"):
        col_a, col_b, col_c = st.columns(3)
        new_t = col_a.text_input("Ticker (e.g. SI=F)").upper()
        new_q = col_b.number_input("Shares/Units", min_value=0.0, step=0.1)
        new_c = col_c.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
        
        if st.button("Commit to Ledger"):
            if new_t:
                current_df = conn.read(spreadsheet=MY_SPREADSHEET, worksheet="Portfolio")
                new_data = pd.DataFrame([{"Ticker": new_t, "Shares": new_q, "Cost": new_c}])
                updated_df = pd.concat([current_df, new_data], ignore_index=True)
                conn.update(spreadsheet=MY_SPREADSHEET, worksheet="Portfolio", data=updated_df)
                st.success(f"Log Updated: {new_t} added.")
                st.rerun()

    st.divider()
    st.subheader("Current Holdings Performance")
    portfolio_df = conn.read(spreadsheet=MY_SPREADSHEET, worksheet="Portfolio", ttl=0)
    
    if not portfolio_df.empty:
        total_value = 0
        for index, row in portfolio_df.iterrows():
            ticker = row['Ticker']
            shares = row.get('Shares', 0)
            
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 0.5])
            
            try:
                live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            except:
                live_p = 0
            
            current_val = shares * live_p
            total_value += current_val
            
            c1.write(f"**{ticker}**")
            c2.write(f"{shares} units")
            c3.write(f"Live: ${live_p:,.2f}")
            c4.write(f"Value: ${current_val:,.2f}")
            
            if c5.button("🗑️", key=f"del_{ticker}_{index}"):
                updated_df = portfolio_df.drop(index)
                conn.update(spreadsheet=MY_SPREADSHEET, worksheet="Portfolio", data=updated_df)
                st.rerun()
                
        st.divider()
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    else:
        st.info("Your portfolio ledger is currently empty.")

# --- TAB 6: TOP 10 (US + Canadian) ---
with tabs[5]:
    st.header("🏆 Momentum Leaderboard")
    
    if st.button("Run Global Scan"):
        # US Stocks
        us_stocks = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "COST"]
        st.subheader("🇺🇸 Top 10 US Stocks")
        us_results = [get_kbot_score(t) for t in us_stocks]
        us_df = pd.DataFrame([r for r in us_results if r]).sort_values("Score", ascending=False)
        st.table(us_df)

        st.divider()
        
        # Canadian Stocks (TSX)
        canadian_stocks = ["SHOP", "RY", "CNQ", "SU", "ENB", "CP", "BN", "ATD", "FTS", "GOLD"]
        st.subheader("🇨🇦 Top 10 Canadian Stocks")
        ca_results = [get_kbot_score(t) for t in canadian_stocks]
        ca_df = pd.DataFrame([r for r in ca_results if r]).sort_values("Score", ascending=False)
        st.table(ca_df)

# --- TAB 7: ETF EXPLORER ---
with tabs[6]:
    st.header("📈 ETF Explorer")
    st.write("Momentum scan for popular US and Canadian ETFs")
    
    if st.button("Scan ETFs"):
        etfs = ["SPY", "QQQ", "VOO", "VTI", "VEA", "VXUS", "XIU.TO", "XIC.TO", "XSP.TO", "XEI.TO", "ZWB.TO", "XQQ.TO"]
        
        results = []
        for etf in etfs:
            time.sleep(1.2)   # Help prevent rate limits
            score = get_kbot_score(etf)
            if score:
                results.append(score)
        
        if results:
            etf_df = pd.DataFrame(results).sort_values("Score", ascending=False)
            st.table(etf_df)
        else:
            st.info("No valid data returned. Try again in a few minutes.")

# --- TAB 8: ANOMALY SCANNER ---
with tabs[7]:
    st.header("🚨 2-Sigma Anomaly Scanner")
    st.write("Detects mathematical anomalies: High volume combined with extreme price deviation.")
    
    default_watch_list = "SPY, QQQ, TLT, GLD, SLV, AAPL, NVDA, TSLA, BTC-USD, SHOP, SU"
    scan_input = st.text_input("Enter Tickers to Scan (comma separated):", default_watch_list)
    
    if st.button("Run Anomaly Scanner"):
        watch_list = [t.strip().upper() for t in scan_input.split(",") if t.strip()]
        run_anomaly_scanner(watch_list)

# --- NEW TAB 9: HIDDEN GEMS ---
with tabs[8]:
    st.header("💎 Small-Cap 'Hidden Gem' Scanner")
    st.write("Generates a deep-dive AI report identifying small-cap stocks ($100M - $2B) with massive growth potential, low analyst coverage, and strong fundamentals.")
    
    if st.button("Run Deep-Dive Small-Cap Scan"):
        with st.spinner("TrinityAI is searching the markets for Hidden Gems. This takes a moment..."):
            try:
                gem_prompt = """You are a senior small-cap equity research analyst at Goldman Sachs who covers companies BEFORE they reach $10 billion in market cap — because by the time Wall Street's big analysts start covering a stock, the easy money has already been made.

I need to find small-cap stocks with 10-100x potential before mainstream analysts discover them.

Scan parameters:
- Market cap filter: focus on companies between $100M and $2B.
- Revenue growth screen: minimum 25% year-over-year revenue growth for 3+ consecutive quarters.
- Analyst coverage check: companies with 0-5 analysts covering them.
- Insider ownership: founders and executives owning 15%+ of shares.
- Industry tailwinds: AI, cybersecurity, energy transition, aging demographics, automation.
- Unit economics quality: improving gross margins and positive operating leverage.
- Balance sheet health: enough cash to survive 18+ months.
- Competitive position: network effects, patents, switching costs, or unique data.
- Near-term catalysts: specific events in the next 6-12 months.

Format as a Goldman Sachs-style small-cap opportunity report with 3-5 specific stock ideas, each meeting multiple criteria above. Be highly specific."""

                # Send the heavy prompt to the Gemini Brain
                response = client.models.generate_content(model="gemini-2.5-flash", contents=gem_prompt)
                
                # Display the formatted report
                st.markdown(response.text)
                st.success("Scan Complete.")
                
            except Exception as e:
                st.error(f"TrinityAI SYSTEM ERROR: {e}")