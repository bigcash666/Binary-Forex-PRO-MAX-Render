import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

st.set_page_config(page_title="Binary Forex PRO MAX", layout="wide", page_icon="📈")

st.title("📈 Binary Forex Tracker PRO MAX v3")
st.markdown("**Полная стратегия:** RSI + MACD + Stochastic + ADX + Bollinger Bands + News Filter")

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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def send_telegram(message):
    token = st.session_state.bot_token
    chat_id = st.session_state.chat_id
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=8)
        except:
            pass

def load_news():
    global news_cache
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
        news_cache = r.json()
    except:
        pass

def has_high_impact_news(pair):
    if not news_cache: return False, ""
    now = datetime.now(timezone.utc)
    pair_map = {
        "EUR/USD": ["EUR","USD"], "GBP/USD": ["GBP","USD"], "USD/JPY": ["USD","JPY"],
        "AUD/USD": ["AUD","USD"], "USD/CAD": ["USD","CAD"], "USD/CHF": ["USD","CHF"],
        "NZD/USD": ["NZD","USD"], "EUR/JPY": ["EUR","JPY"], "XAU/USD": ["USD"]
    }
    currencies = pair_map.get(pair, ["USD"])
    for ev in news_cache:
        try:
            dt = datetime.strptime(ev['date'] + " " + ev.get('time','00:00'), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            diff = (dt - now).total_seconds() / 60
            if -30 < diff < 25:
                if any(c in ev.get('country','').upper() for c in currencies) and ev.get('impact','').lower() in ['high','red']:
                    return True, ev.get('title','')
        except:
            continue
    return False, ""

def clean_data(data):
    return [x for x in data if x is not None]

# ==================== ИНДИКАТОРЫ ====================
def calculate_rsi(closes):
    closes = clean_data(closes)
    if len(closes) < 15: return 50.0
    gains = losses = 0.0
    for i in range(1, 15):
        change = closes[i] - closes[i-1]
        if change > 0: gains += change
        else: losses -= change
    avg_gain = gains / 14
    avg_loss = losses / 14
    last = closes[-1] - closes[-2]
    if last > 0:
        avg_gain = (avg_gain * 13 + last) / 14
        avg_loss = avg_loss * 13 / 14
    else:
        avg_gain = avg_gain * 13 / 14
        avg_loss = (avg_loss * 13 + abs(last)) / 14
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    return 100 - (100 / (1 + rs))

def calculate_ema(data, period):
    data = clean_data(data)
    if len(data) < period: return [data[-1]] * len(data) if data else [0]
    k = 2 / (period + 1)
    ema = [data[0]]
    for i in range(1, len(data)):
        ema.append(data[i] * k + ema[i-1] * (1 - k))
    return ema

def calculate_macd_lines(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 =
