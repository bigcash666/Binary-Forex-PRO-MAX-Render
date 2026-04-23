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

# ==================== ФУНКЦИИ ====================
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

def load_news():
    global news_cache
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
        news_cache = r.json()
    except:
        news_cache = []

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
            dt_str = ev['date'] + " " + ev.get('time', '00:00')
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except:
            continue
        diff = (dt - now).total_seconds() / 60
        if -30 < diff < 25:
            if any(c.upper() in ev.get('country', '').upper() for c in currencies) and ev.get('impact', '').lower() in ['high', 'red']:
                return True, ev.get('title', '')
    return False, ""

# ==================== ИНДИКАТОРЫ ====================
def calculate_rsi(closes):
    if len(closes) < 15:
        return 50.0
    gains = losses = 0.0
    for i in range(1, 15):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / 14
    avg_loss = losses / 14
    last_change = closes[-1] - closes[-2]
    if last_change > 0:
        avg_gain = (avg_gain * 13 + last_change) / 14
        avg_loss = avg_loss * 13 / 14
    else:
        avg_gain = avg_gain * 13 / 14
        avg_loss = (avg_loss * 13 + abs(last_change)) / 14
    rs = (avg_gain / avg_loss) if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(data, period):
    if len(data) < period:
        return [data[0]] * len(data)
    k = 2 / (period + 1)
    ema = [data[0]]
    for i in range(1, len(data)):
        ema_value = data[i] * k + ema[-1] * (1 - k)
        ema.append(ema_value)
    return ema

def calculate_macd_lines(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(ema12))]
    signal_line = calculate_ema(macd_line, 9)
    return macd_line, signal_line

def calculate_stochastic(highs, lows, closes):
    if len(closes) < 20:
        return 50, 50
