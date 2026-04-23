import streamlit as st
import requests
from datetime import datetime, timezone

st.set_page_config(page_title="Binary Forex PRO MAX", layout="wide", page_icon="📈")

st.title("📈 Binary Forex Tracker PRO MAX v3 — Render Edition")
st.markdown("**RSI + MACD + Stochastic + ADX + Bollinger + News Filter** • Работает 24/7")

# ==================== НАСТРОЙКИ ====================
if "bot_token" not in st.session_state:
    st.session_state.bot_token = ""
if "chat_id" not in st.session_state:
    st.session_state.chat_id = ""

DEFAULT_PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X", "EUR/JPY": "EURJPY=X", "XAU/USD": "GC=F"
}

news_cache = []

# ==================== TELEGRAM ====================
def send_telegram(message):
    token = st.session_state.bot_token
    chat_id = st.session_state.chat_id
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=8
            )
        except:
            pass

# ==================== НОВОСТИ ====================
def load_news():
    global news_cache
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
        news_cache = r.json()
    except:
        pass

def has_high_impact_news(pair):
    if not news_cache:
        return False, ""
    now = datetime.now(timezone.utc)
    pair_map = {
        "EUR/USD": ["EUR","USD"], "GBP/USD": ["GBP","USD"], "USD/JPY": ["USD","JPY"],
        "AUD/USD": ["AUD","USD"], "USD/CAD": ["USD","CAD"], "USD/CHF": ["USD","CHF"],
        "NZD/USD": ["NZD","USD"], "EUR/JPY": ["EUR","JPY"], "XAU/USD": ["USD"]
    }
    currencies = pair_map.get(pair, ["USD"])
    
    for ev in news_cache:
        try:
            dt = datetime.strptime(ev['date'] + " " + ev.
