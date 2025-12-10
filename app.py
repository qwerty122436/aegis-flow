import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import time
import os

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Aegis Pro: Risk & FOMO", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #FAFAFA; }
    .high-prob { color: #00ff41; font-weight: bold; }
    .missed-gain { color: #facc15; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'last_fomo_check' not in st.session_state:
    st.session_state['last_fomo_check'] = datetime.now()

SHADOW_FILE = "shadow_ledger.csv"

# ==========================================
# 2. EMAIL ENGINE
# ==========================================
def send_email(to_email, password, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = to_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(to_email, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# ==========================================
# 3. SHADOW LEDGER (Tracks Missed Trades)
# ==========================================
def log_shadow_trade(symbol, action, price, prob):
    """Saves rejected trades to a CSV file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = pd.DataFrame([[timestamp, symbol, action, price, prob]], 
                           columns=['Time', 'Symbol', 'Action', 'Price', 'Prob'])
    
    if not os.path.isfile(SHADOW_FILE):
        new_row.to_csv(SHADOW_FILE, index=False)
    else:
        new_row.to_csv(SHADOW_FILE, mode='a', header=False, index=False)

def generate_fomo_report():
    """Analyzes the shadow ledger to see what we missed"""
    if not os.path.isfile(SHADOW_FILE):
        return None

    df = pd.read_csv(SHADOW_FILE)
    if df.empty: return None

    report = "FOMO REPORT: MISSED OPPORTUNITIES (Last 48h)\n------------------------------------------\n"
    missed_count = 0

    # Check current prices
    unique_symbols = df['Symbol'].unique()
    current_prices = {}
    
    try:
        data = yf.download(list(unique_symbols), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        # Handle single vs multiple ticker return formats
        if len(unique_symbols) == 1:
            current_prices[unique_symbols[0]] = float(data)
        else:
            for sym in unique_symbols:
                current_prices[sym] = float(data[sym])
    except:
        return "Error fetching current prices for report."

    # Calculate "What If" scenarios
    for index, row in df.iterrows():
        sym = row['Symbol']
        entry = row['Price']
        action = row['Action']
        curr = current_prices.get(sym, 0)
        
        if curr == 0: continue

        # Calculate Profit if we had taken the trade
        profit_pct = 0
        if action == "BUY":
            profit_pct = ((curr - entry) / entry) * 100
        elif action == "SELL":
            profit_pct = ((entry - curr) / entry) * 100 # Short profit logic

        # Only report if it would have made > 0.5% profit
        if profit_pct > 0.5:
            missed_count += 1
            report += f"[MISSED] {sym} ({action}) | Entry: {entry:.4f} -> Now: {curr:.4f} | Gain: +{profit_pct:.2f}%\n"

    if missed_count == 0:
        return None # No big missed trades
    
    # Clear the file after reporting so we don't repeat old news
    os.remove(SHADOW_FILE)
    return report

# ==========================================
# 4. TRADING BRAIN (RSI + Probability)
# ==========================================
def analyze_market(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="14d", interval="60m") # 1-hour candles
        if df.empty: return None

        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        rsi = df['rsi'].iloc[-1]
        price = df['Close'].iloc[-1]
        
        # PROBABILITY LOGIC
        # Extreme RSI means higher probability of reversal
        prob = 50
        signal = "WAIT"
        
        if rsi < 25:
            signal = "BUY"
            prob = 85 # Very High Prob
        elif rsi < 35:
            signal = "BUY"
            prob = 65 # Medium Prob
        elif rsi > 75:
            signal = "SELL"
            prob = 85 # Very High Prob
        elif rsi > 65:
            signal = "SELL"
            prob = 65 # Medium Prob
            
        return signal, price, rsi, prob
    except:
        return None

# ==========================================
# 5. DASHBOARD & LOOP
# ==========================================
st.sidebar.title("🧠 AEGIS PRO")
user_email = st.sidebar.text_input("Gmail")
user_pass = st.sidebar.text_input("App Password", type="password")
pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD"]

st.title("Aegis: Probability & FOMO Engine")
log_box = st.empty()
countdown_box = st.empty()

if st.sidebar.button("🔴 START INTELLIGENCE CYCLE", type="primary"):
    if not user_email: st.stop()
    
    st.toast("System Active. Monitoring Probability > 70%", icon="📡")
    
    while True:
        # --- A. CHECK FOMO REPORT (Every 48 hours) ---
        time_diff = datetime.now() - st.session_state['last_fomo_check']
        if time_diff > timedelta(hours=48):
            st.toast("Generating FOMO Report...", icon="📊")
            fomo_msg = generate_fomo_report()
            if fomo_msg:
                send_email(user_email, user_pass, "📅 AEGIS: 2-Day Missed Opportunities", fomo_msg)
            st.session_state['last_fomo_check'] = datetime.now()

        # --- B. SCAN MARKETS ---
        for pair in pairs:
            result = analyze_market(pair)
            if not result: continue
            
            signal, price, rsi, prob = result
            timestamp = datetime.now().strftime("%H:%M")
            
            log_msg = f"[{timestamp}] {pair} | {signal} | RSI:{rsi:.0f} | WinProb:{prob}%"
            
            # --- C. DECISION TREE ---
            if prob >= 70 and signal != "WAIT":
                # SCENARIO 1: HIGH PROBABILITY -> SEND EMAIL IMMEDIATELY
                log_box.markdown(f"🔥 **ACTION:** {log_msg}")
                subject = f"🚨 {signal} ALERT: {pair} (Prob: {prob}%)"
                body = f"""
                HIGH PROBABILITY TRADE DETECTED
                -------------------------------
                Asset: {pair}
                Action: {signal}
                Price: {price}
                RSI: {rsi:.1f} (Extreme)
                Win Probability: {prob}%
                
                Execute immediately.
                """
                send_email(user_email, user_pass, subject, body)
                
            elif prob >= 50 and signal != "WAIT":
                # SCENARIO 2: MEDIUM PROBABILITY -> DON'T EMAIL, BUT LOG TO SHADOW LEDGER
                log_box.info(f"💾 Logged to Shadow Ledger: {log_msg}")
                log_shadow_trade(pair, signal, price, prob)
            
            else:
                # SCENARIO 3: NO ACTION
                log_box.text(log_msg)

        # Countdown 10 minutes
        for i in range(600, 0, -1):
            countdown_box.metric("Next Scan In", f"{i}s")
            time.sleep(1)
