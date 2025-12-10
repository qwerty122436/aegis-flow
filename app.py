import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Aegis 10-Min Bot", page_icon="⚡", layout="wide")

# Custom Styles
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #FAFAFA; }
    .high-prob { color: #00ff41; font-weight: bold; }
    .high-risk { color: #ff0041; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Session State for Timer
if 'next_scan' not in st.session_state:
    st.session_state['next_scan'] = datetime.now()

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
        st.error(f"Email Error: {e}")
        return False

# ==========================================
# 3. MATH ENGINE (Risk & Probability)
# ==========================================
def calculate_metrics(df):
    # 1. RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 2. ATR (Average True Range) for Volatility Risk
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    return df

def analyze_pair(symbol):
    try:
        # Fetch live data (1h interval, last 7 days)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="7d", interval="60m")
        
        if df.empty: return None

        df = calculate_metrics(df)
        
        current_price = df['Close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # --- PROBABILITY LOGIC ---
        # RSI < 30 = High Probability of Buy Success
        # RSI > 70 = High Probability of Sell Success
        if rsi < 30:
            signal = "BUY"
            win_prob = 75 + (30 - rsi) # Example: RSI 20 -> 85% Win Prob
        elif rsi > 70:
            signal = "SELL"
            win_prob = 75 + (rsi - 70) # Example: RSI 80 -> 85% Win Prob
        else:
            signal = "WAIT"
            win_prob = 50 # Coin toss
            
        # --- RISK LOGIC ---
        # Volatility Risk (ATR as % of Price)
        volatility_pct = (atr / current_price) * 100
        if volatility_pct > 0.5: 
            risk_level = "HIGH"
        elif volatility_pct > 0.2: 
            risk_level = "MEDIUM"
        else: 
            risk_level = "LOW"
            
        return {
            "symbol": symbol,
            "signal": signal,
            "price": current_price,
            "rsi": rsi,
            "win_prob": min(win_prob, 99), # Cap at 99%
            "risk": risk_level
        }
    except:
        return None

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.sidebar.title("⚡ AEGIS 10-MIN BOT")
user_email = st.sidebar.text_input("Gmail Address")
user_pass = st.sidebar.text_input("App Password", type="password")

# Multi-Asset Scanner
pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
st.title("High-Frequency Forex Scanner")

log_box = st.empty()
timer_box = st.empty()

# ==========================================
# 5. THE 10-MINUTE LOOP
# ==========================================
if st.sidebar.button("🔴 START 10-MIN CYCLE", type="primary"):
    if not user_email or not user_pass:
        st.error("Enter credentials first.")
        st.stop()
    
    st.toast("Cycle Started. Email incoming every 10 mins.", icon="⏳")
    
    while True:
        # 1. SCAN ALL PAIRS
        results = []
        for pair in pairs:
            res = analyze_pair(pair)
            if res: results.append(res)
            
        # 2. FIND BEST TRADE
        # Sort by Win Probability (Highest first)
        results.sort(key=lambda x: x['win_prob'], reverse=True)
        best_trade = results[0]
        
        timestamp = datetime.now().strftime("%H:%M")
        
        # 3. DISPLAY ON SCREEN
        msg = f"[{timestamp}] Best Option: {best_trade['symbol']} | {best_trade['signal']} | Prob: {best_trade['win_prob']:.1f}%"
        log_box.info(msg)
        
        # 4. SEND EMAIL (EVERY 10 MINS)
        subject = f"⚡ {best_trade['signal']} ALERT: {best_trade['symbol']}"
        body = f"""
        AEGIS HF UPDATE ({timestamp})
        -----------------------------
        Best Asset: {best_trade['symbol']}
        Action: {best_trade['signal']}
        Price: {best_trade['price']:.5f}
        
        📊 STATISTICS:
        Win Probability: {best_trade['win_prob']:.1f}%
        Risk Level: {best_trade['risk']}
        RSI: {best_trade['rsi']:.1f}
        
         Next scan in 10 minutes...
        """
        
        send_email(user_email, user_pass, subject, body)
        
        # 5. COUNTDOWN TIMER (600 seconds)
        for seconds_left in range(600, 0, -1):
            timer_box.metric("Next Email In", f"{seconds_left // 60}m {seconds_left % 60}s")
            time.sleep(1)
