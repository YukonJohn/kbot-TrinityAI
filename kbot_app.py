import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests
from google import genai
from google.cloud import firestore
from google.oauth2 import service_account

# ====================== CONFIG & SECURITY ======================
st.set_page_config(page_title="TrinityAI Master Controller", layout="wide")

# --- FIREBASE AUTHENTICATION KEYS ---
FIREBASE_API_KEY = "AIzaSyA9LHDJ5INvHDYRZN0mHEzJmruvu084Qmw"

def firebase_sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response.json()

def firebase_sign_up(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response.json()

# --- USER SESSION & AUTHENTICATION SIDEBAR ---
st.sidebar.title("🔐 Account Access")

if "user_info" not in st.session_state:
    st.session_state.user_info = None

if not st.session_state.user_info:
    auth_mode = st.sidebar.radio("Select Action", ["Sign In", "Create Account"])
    email_input = st.sidebar.text_input("Email:")
    pass_input = st.sidebar.text_input("Password:", type="password")

    if auth_mode == "Sign In":
        if st.sidebar.button("Sign In"):
            if email_input and pass_input:
                res = firebase_sign_in(email_input, pass_input)
                if "idToken" in res:
                    st.session_state.user_info = res
                    st.sidebar.success("🟢 Signed In Successfully!")
                    st.rerun()
                else:
                    err_msg = res.get("error", {}).get("message", "Authentication Failed")
                    st.sidebar.error(f"Error: {err_msg}")
            else:
                st.sidebar.warning("Please provide both email and password.")

    elif auth_mode == "Create Account":
        if st.sidebar.button("Register Account"):
            if email_input and pass_input:
                res = firebase_sign_up(email_input, pass_input)
                if "idToken" in res:
                    st.session_state.user_info = res
                    st.sidebar.success("🎉 Account Created & Signed In!")
                    st.rerun()
                else:
                    err_msg = res.get("error", {}).get("message", "Registration Failed")
                    st.sidebar.error(f"Error: {err_msg}")
            else:
                st.sidebar.warning("Please provide both email and password.")

    st.info("👋 Welcome to TrinityAI. Please Sign In or Create an Account in the sidebar to access Kbot.")
    st.stop()
else:
    user_email = st.session_state.user_info.get("email", "User")
    st.sidebar.write(f"Logged in as: **{user_email}**")
    if st.sidebar.button("Sign Out"):
        st.session_state.user_info = None
        st.rerun()

# --- HARDCODED GEMINI API KEY ---
MY_API_KEY = "AIzaSyA9LHDJ5INvHDYRZN0mHEzJmruvu084Qmw"

# Initialize Gemini AI directly
client = genai.Client(api_key=MY_API_KEY)

# --- CONNECT TO FIRESTORE CLOUD VAULT (VIA SECRETS) ---
try:
    key_dict = dict(st.secrets["firestore"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    st.sidebar.success("🟢 Connected to Cloud Vault")
except Exception as e:
    st.error(f"🔴 Database Connection Failed: {e}")
    st.stop()

# ====================== AI & SCORING LOGIC ======================
def get_stock_description(ticker):
    try:
        prompt = (f"Act as a professional commodities and stock market analyst in 2026. "
                  f"Give a deep, strategic analysis of the ticker {ticker}. "
                  f"Explain what it is (stock, metal, futures, etc.), current market conditions, "
                  f"key drivers, recent performance, and outlook for the rest of 2026. "
                  f"Keep it professional and useful for a trader. Use 5-6 clear sentences.")
        
        response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
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

# --- ANOMALY SCANNER ---
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

# --- AMANITA SCANNER ---
def run_amanita_scanner(tickers):
    st.subheader("🍄 Amanita: Qullamaggie 5-Star Momentum Scanner")
    st.write("Scanning for massive momentum, high liquidity, stacked EMAs, and volatility contraction.")
    
    with st.spinner('Amanita is analyzing price action and moving averages...'):
        results = []
        for ticker in tickers:
            try:
                data = yf.Ticker(ticker).history(period="6mo")
                if data.empty or len(data) < 50:
                    continue
                    
                current_price = data['Close'].iloc[-1]
                dollar_vol = current_price * data['Volume'].tail(20).mean()
                
                data['EMA_10'] = data['Close'].ewm(span=10).mean()
                data['EMA_20'] = data['Close'].ewm(span=20).mean()
                data['EMA_50'] = data['Close'].ewm(span=50).mean()
                
                p_1mo = data['Close'].iloc[-21] if len(data) >= 21 else data['Close'].iloc[0]
                p_3mo = data['Close'].iloc[-63] if len(data) >= 63 else data['Close'].iloc[0]
                p_6mo = data['Close'].iloc[0]
                
                perf_1mo = ((current_price - p_1mo) / p_1mo) * 100
                perf_3mo = ((current_price - p_3mo) / p_3mo) * 100
                perf_6mo = ((current_price - p_6mo) / p_6mo) * 100
                max_perf = max(perf_1mo, perf_3mo, perf_6mo)
                
                data['Daily_Range_Pct'] = ((data['High'] - data['Low']) / data['Close']) * 100
                adr_20 = data['Daily_Range_Pct'].tail(20).mean()
                
                has_momentum = max_perf >= 30.0
                is_liquid = dollar_vol >= 5_000_000
                is_volatile = adr_20 >= 4.0
                
                ema_10 = data['EMA_10'].iloc[-1]
                ema_20 = data['EMA_20'].iloc[-1]
                ema_50 = data['EMA_50'].iloc[-1]
                
                trend_stacked = (ema_10 > ema_20) and (ema_20 > ema_50) and (current_price > ema_10)
                
                surfing_10 = abs((current_price - ema_10) / ema_10) < 0.04
                surfing_20 = abs((current_price - ema_20) / ema_20) < 0.04
                is_surfing = surfing_10 or surfing_20
                
                score = sum([has_momentum, is_liquid, is_volatile, trend_stacked, is_surfing])
                
                if score >= 3:
                    results.append({
                        "Ticker": ticker,
                        "Score": f"{score}/5",
                        "Momentum": f"+{max_perf:.1f}%",
                        "ADR (Vol)": f"{adr_20:.1f}%",
                        "EMAs Stacked": "✅" if trend_stacked else "❌",
                        "Surfing": "✅" if is_surfing else "❌",
                        "Signal": "⭐ 5-STAR SETUP" if score == 5 else "On Watch"
                    })
            except Exception:
                continue
                
        if results:
            df = pd.DataFrame(results).sort_values(by=["Score", "Momentum"], ascending=[False, False])
            st.dataframe(df, use_container_width=True)
            if any(r["Score"] == "5/5" for r in results):
                st.success("🚨 Amanita found a perfect 5-Star Setup!")
        else:
            st.info("Market is quiet. No stocks passed the strict Amanita criteria today.")

# ====================== INTERFACE ======================
st.title("🤖 Kbot: TrinityAI Master Controller")

tabs = st.tabs(["📊 Analyzer", "🚀 Trends", "🌍 Global Pulse", "⛏️ Mining Scanner", 
                "📁 My Portfolio", "🏆 Top 10", "📈 ETF Explorer", "🚨 Anomaly Scanner", "💎 Hidden Gems", "🍄 Amanita"])

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
                response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
                st.subheader("Strategic Market Briefing")
                st.info(response.text)
            except Exception as e:
                st.error(f"TrinityAI SYSTEM ERROR: {e}")

# --- TAB 3: GLOBAL PULSE ---
with tabs[2]:
    st.header("Gemini AI Analysis")
    if st.button("Generate AI Market Report"):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents="Summarize the current market outlook for Silver.")
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

# --- TAB 5: MY PORTFOLIO (FIRESTORE) ---
with tabs[4]:
    st.header("📁 TrinityAI Portfolio Command")
    
    with st.expander("➕ Add New Holdings"):
        col_a, col_b, col_c = st.columns(3)
        new_t = col_a.text_input("Ticker (e.g. SI=F)").upper()
        new_q = col_b.number_input("Shares/Units", min_value=0.0, step=0.1)
        new_c = col_c.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
        
        if st.button("Commit to Cloud Vault"):
            if new_t:
                doc_ref = db.collection("portfolio").document(new_t)
                doc_ref.set({
                    "Ticker": new_t,
                    "Shares": new_q,
                    "Cost": new_c
                })
                st.success(f"Log Updated: {new_t} saved to Firestore.")
                st.rerun()

    st.divider()
    st.subheader("Current Holdings Performance")
    
    portfolio_ref = db.collection("portfolio").stream()
    portfolio_data = [doc.to_dict() for doc in portfolio_ref]
    
    if portfolio_data:
        total_value = 0
        for item in portfolio_data:
            ticker = item.get('Ticker', '')
            shares = item.get('Shares', 0.0)
            
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
            
            if c5.button("🗑️", key=f"del_{ticker}"):
                db.collection("portfolio").document(ticker).delete()
                st.rerun()
                
        st.divider()
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    else:
        st.info("Your portfolio ledger is currently empty.")

# --- TAB 6: TOP 10 ---
with tabs[5]:
    st.header("🏆 Momentum Leaderboard")
    
    if st.button("Run Global Scan"):
        us_stocks = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "COST"]
        st.subheader("🇺🇸 Top 10 US Stocks")
        us_results = [get_kbot_score(t) for t in us_stocks]
        us_df = pd.DataFrame([r for r in us_results if r]).sort_values("Score", ascending=False)
        st.table(us_df)

        st.divider()
        
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
            time.sleep(1.2)
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

# --- TAB 9: HIDDEN GEMS ---
with tabs[8]:
    st.header("💎 Small-Cap 'Hidden Gem' Scanner")
    st.write("Generates a deep-dive AI report identifying US & Canadian small-cap stocks ($100M - $2B) with massive growth potential.")
    
    if st.button("Run Deep-Dive Small-Cap Scan"):
        with st.spinner("TrinityAI is searching US and Canadian markets for Hidden Gems. This takes a moment..."):
            try:
                gem_prompt = """You are a senior small-cap equity research analyst at Goldman Sachs who covers companies BEFORE they reach $10 billion in market cap.

I need to find small-cap stocks with 10-100x potential before mainstream analysts discover them.

CRITICAL CONSTRAINT: ONLY include companies publicly traded on United States (NYSE, NASDAQ, AMEX) or Canadian (TSX, TSXV, CSE) stock exchanges. Do NOT include international exchanges or purely OTC stocks. Provide their exact ticker symbols.

Scan parameters:
- Geography: US and Canadian exchanges ONLY.
- Market cap filter: focus on companies between $100M and $2B.
- Revenue growth screen: minimum 25% year-over-year revenue growth for 3+ consecutive quarters.
- Analyst coverage check: companies with 0-5 analysts covering them.
- Insider ownership: founders and executives owning 15%+ of shares.
- Industry tailwinds: AI, cybersecurity, energy transition, aging demographics, automation.
- Unit economics quality: improving gross margins and positive operating leverage.
- Balance sheet health: enough cash to survive 18+ months.
- Competitive position: network effects, patents, switching costs, or unique data.
- Near-term catalysts: specific events in the next 6-12 months.

Format as a Goldman Sachs-style small-cap opportunity report with 3-5 specific stock ideas, each meeting multiple criteria above."""

                response = client.models.generate_content(model="gemini-3.6-flash", contents=gem_prompt)
                st.markdown(response.text)
                st.success("Scan Complete.")
                
            except Exception as e:
                st.error(f"TrinityAI SYSTEM ERROR: {e}")

# --- TAB 10: AMANITA SCANNER ---
with tabs[9]:
    st.header("🍄 Amanita: 5-Star Quant Scanner")
    st.write("Identifies high-momentum breakout setups using institutional swing trading logic.")
    
    default_amanita_list = "HOOD, COIN, PLTR, NVDA, TSLA, SMCI, UBER, CRWD, SHOP, SU"
    amanita_input = st.text_input("Enter Tickers to Scan for 5-Star Setups:", default_amanita_list)
    
    if st.button("Run Amanita Scanner"):
        amanita_watch_list = [t.strip().upper() for t in amanita_input.split(",") if t.strip()]
        run_amanita_scanner(amanita_watch_list)