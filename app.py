import streamlit as st
import pandas as pd
import ccxt
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Aegis Auto-Bot", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #FAFAFA; }
    .log-box { font-family: 'Courier New', monospace; color: #00f2ff; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State to remember the last email sent
if 'last_alert' not in st.session_state:
    st.session_state['last_alert'] = "NONE"

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
# 3. LIVE MARKET BRAIN
# ==========================================
def fetch_and_analyze(symbol):
    """
    Connects to Binance, gets data, calculates RSI.
    """
    try:
        exchange = ccxt.binance()
        # Get last 50 hours of data
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate RSI (The Indicator)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current_price = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        
        # DECISION LOGIC
        if current_rsi < 30:
            return "BUY", current_price, current_rsi
        elif current_rsi > 70:
            return "SELL", current_price, current_rsi
        else:
            return "WAIT", current_price, current_rsi
            
    except Exception as e:
        return "ERROR", 0, 0

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.sidebar.title("🛡️ AEGIS AUTO-CONFIG")

# Credentials
user_email = st.sidebar.text_input("Gmail Address")
user_pass = st.sidebar.text_input("App Password", type="password")

# Target
symbol = st.sidebar.selectbox("Asset to Watch", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
interval = st.sidebar.slider("Scan Interval (Seconds)", 10, 300, 60)

st.title(f"Aegis Sentinel: {symbol}")
st.write("System status: **IDLE**")

# Placeholders for live updates (so the page doesn't glitch)
price_metric = st.empty()
status_metric = st.empty()
log_area = st.empty()
chart_area = st.empty()

# ==========================================
# 5. THE INFINITE LOOP
# ==========================================
if st.sidebar.button("🔴 ACTIVATE SENTINEL", type="primary"):
    
    if not user_email or not user_pass:
        st.error("⚠️ STOP: You must enter your Email and App Password first.")
        st.stop()
        
    st.toast("Sentinel Active. Do not close this tab.", icon="👁️")
    
    logs = []
    
    # This loop runs forever until you close the tab
    while True:
        # 1. Get Real Data
        decision, price, rsi = fetch_and_analyze(symbol)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 2. Update Dashboard UI
        price_metric.metric("Live Price", f"${price:,.2f}", f"RSI: {rsi:.1f}")
        
        # 3. Check for Signals
        if decision == "BUY" and st.session_state['last_alert'] != "BUY":
            # TRIGGER BUY EMAIL
            status_metric.error(f"🚨 BUY SIGNAL DETECTED AT {timestamp}")
            email_body = f"Price: ${price}\nRSI: {rsi}\n\nThe asset is OVERSOLD. Price is low. Good time to enter."
            send_email(user_email, user_pass, f"🚀 BUY ALERT: {symbol}", email_body)
            st.session_state['last_alert'] = "BUY" # Prevent spamming
            st.toast("Email Sent!", icon="📧")
            
        elif decision == "SELL" and st.session_state['last_alert'] != "SELL":
            # TRIGGER SELL EMAIL
            status_metric.success(f"💰 SELL SIGNAL DETECTED AT {timestamp}")
            email_body = f"Price: ${price}\nRSI: {rsi}\n\nThe asset is OVERBOUGHT. Price is high. Good time to take profits."
            send_email(user_email, user_pass, f"📉 SELL ALERT: {symbol}", email_body)
            st.session_state['last_alert'] = "SELL" # Prevent spamming
            st.toast("Email Sent!", icon="📧")
            
        else:
            status_metric.info(f"Scanning... Market is stable. ({timestamp})")

        # 4. Maintain Log
        log_entry = f"[{timestamp}] Price: ${price:.2f} | RSI: {rsi:.1f} | Action: {decision}"
        logs.insert(0, log_entry) # Add new log to top
        log_area.text_area("Live System Logs", "\n".join(logs[:10]), height=200)
        
        # 5. Wait for next scan
        time.sleep(interval)
