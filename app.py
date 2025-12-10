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
st.set_page_config(page_title="Aegis Pro: 55% Threshold", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #FAFAFA; }
    .high-prob { color: #00ff41; font-weight: bold; }
    .missed-gain { color: #facc15; font-style: italic; }
</style>
""", unsafe_allow_html=True)

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

    report = "FOMO REPORT: TRADES > 50% (Last 48h)\n------------------------------------------\n"
    missed_count = 0

    unique_symbols = df['Symbol'].unique()
    current_prices = {}
    
    try:
        # Fetch current prices to compare
        data = yf.download(list(unique_symbols), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        if len(unique_symbols) == 1:
            current_prices[unique_symbols[0]] = float(data)
        else:
            for sym in unique_symbols:
                current_prices[sym] = float(data[sym])
    except:
        return "Error fetching prices for report."

    for index, row in df.iterrows():
        sym = row['Symbol']
        entry = row['Price']
        action = row['Action']
        prob = row['Prob']
        curr = current_prices.get(sym, 0)
