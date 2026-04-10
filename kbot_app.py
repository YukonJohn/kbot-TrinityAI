import streamlit as st
import yfinance as yf
import pandas as pd
import time
from google import genai
from streamlit_gsheets import GSheetsConnection

# ====================== CONFIG & SECURITY ======================
st.set_page_config(page_title="TrinityAI Master Controller", layout="wide")

# PASSWORD PROTECTION (Case Sensitive)
password_guess = st.sidebar.text_input("Unlock TrinityAI:", type="password")
if password_guess != "Trinity":
    st.info("Enter password (Trinity) in sidebar to begin.")
    st.stop()

# --- SECURE CREDENTIALS (Reading from secrets.toml) ---
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
        # Better prompt that works for stocks, metals, and futures
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

# ====================== INTERFACE ======================
st.title("🤖 Kbot: TrinityAI Master Controller")

tabs = st.tabs(["📊 Analyzer", "🚀 Trends", "🌍 Global Pulse", "⛏️ Mining Scanner", "📁 My Portfolio", "🏆 Top 10"])

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
            
            # Small delay to help with yfinance rate limits
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
            time.sleep(1)  # Small delay to reduce rate limit risk
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

# --- TAB 5: MY PORTFOLIO (WITH DELETE) ---
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

# --- TAB 6: TOP 10 ---
with tabs[5]:
    st.header("🏆 Momentum Leaderboard")
    if st.button("Run Global Scan"):
        scantest = ["AAPL", "NVDA", "TSLA", "AMD", "SI=F", "GC=F", "MSFT", "GOOGL", "AMZN", "META"]
        results = [get_kbot_score(t) for t in scantest]
        final_df = pd.DataFrame([r for r in results if r]).sort_values("Score", ascending=False)
        st.table(final_df)