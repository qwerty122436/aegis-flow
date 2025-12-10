import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# ==========================================
# 1. VISUAL CONFIGURATION (The Aesthetic)
# ==========================================
st.set_page_config(
    page_title="Aegis Flow",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for that "Clean Technical" look
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #FAFAFA;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #41444b;
    }
    div[data-testid="stSidebar"] {
        background-color: #262730;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. THE AI SIMULATION ENGINE
# ==========================================
def get_mock_data():
    """Generates fake crypto market data for demonstration"""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='H')
    prices = np.cumsum(np.random.randn(100)) + 45000  # Random walk around $45k
    return pd.DataFrame({'timestamp': dates, 'price': prices})

def ai_prediction(mode):
    """Simulates the AI analyzing the market"""
    confidence = np.random.randint(40, 95)  # Random confidence 40-95%
    
    if mode == "Fortress (Safe)":
        if confidence > 80:
            return "BUY", confidence
        else:
            return "HOLD", confidence
    else: # Vanguard (Risk)
        decision = np.random.choice(["BUY", "SELL", "HOLD"])
        return decision, confidence

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("🛡️ AEGIS FLOW")
st.sidebar.markdown("---")

# The Mode Switcher
mode = st.sidebar.radio(
    "Select Operation Mode:",
    ("Fortress (Safe)", "Vanguard (High Risk)")
)

st.sidebar.markdown("---")
st.sidebar.write("### 💳 Wallet Integration")
st.sidebar.info("Touch 'n Go Gateway: **Active**")
st.sidebar.text("Balance: $4,250.00 USDT")

if st.sidebar.button("Request Withdrawal"):
    st.sidebar.success("Withdrawal request sent to P2P Agent.")

# ==========================================
# 4. MAIN DASHBOARD
# ==========================================
st.title("Live Market Terminal")

# Top Level Metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Bitcoin (BTC)", value="$45,230.50", delta="+1.2%")
with col2:
    st.metric(label="24h Profit", value="+$124.00", delta="High Risk Mode")
with col3:
    status_color = "green" if mode == "Fortress (Safe)" else "orange"
    st.markdown(f"**System Status:** :{status_color}[ONLINE - {mode}]")

# The Chart
data = get_mock_data()
fig = go.Figure()
fig.add_trace(go.Scatter(x=data['timestamp'], y=data['price'], mode='lines', name='BTC/USDT', line=dict(color='#00f2ff')))
fig.update_layout(
    title="Price Action Analysis",
    paper_bgcolor='#0e1117',
    plot_bgcolor='#0e1117',
    font=dict(color='white'),
    height=400
)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. AI DECISION PANEL
# ==========================================
st.subheader("🤖 AI Neural Engine Output")

if st.button("Analyze Market Now"):
    with st.spinner('AI is reading market signals...'):
        time.sleep(2) # Fake processing time
        decision, win_prob = ai_prediction(mode)
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### Suggested Action")
            if decision == "BUY":
                st.markdown(f"<h1 style='color: #00ff41;'>BUY LONG</h1>", unsafe_allow_html=True)
            elif decision == "SELL":
                st.markdown(f"<h1 style='color: #ff0041;'>SELL SHORT</h1>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h1 style='color: #ffd700;'>HOLD POSITIONS</h1>", unsafe_allow_html=True)
        
        with c2:
            st.markdown("#### Win Probability")
            st.progress(win_prob / 100)
            st.markdown(f"## {win_prob}% Confidence")

        if win_prob < 50:
            st.warning("⚠️ Risk Alert: Probability is low. Trade not recommended.")
        elif win_prob > 80:
            st.success("✅ AI Confidence High. Execution authorized.")