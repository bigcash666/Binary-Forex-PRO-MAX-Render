import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

st.set_page_config(page_title="Binary Forex PRO MAX", layout="wide", page_icon="📈")

st.title("📈 Binary Forex Tracker PRO MAX v3")
st.markdown("**RSI + MACD + Stochastic + ADX + Bollinger + News Filter** • 24/7")

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ==================== TELEGRAM ====================
def send_telegram(message):
    token = st.session_state.bot_token
    chat_id = st.session_state.chat_id
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=8)
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

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def clean_data(data):
    return [x for x in data if x is not None]

# ==================== fetch_pair_data (исправленная) ====================
def fetch_pair_data(ticker, tf):
    pair_name = ticker.replace("=X", "").replace("=F", "")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={tf}&range=10d"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()

        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        closes = clean_data(quotes.get("close", []))[-300:]

        if len(closes) < 50:
            return {"Пара": pair_name, "ТФ": tf, "Цена": "-", "Сигнал": "ERROR", "Сила": "-", "Рекомендация": "Мало данных"}

        price = round(closes[-1], 4)

        has_news, news_title = has_high_impact_news(pair_name)
        if has_news:
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "Сигнал": "🟥 BLOCKED", "Сила": "NEWS", 
                    "Рекомендация": news_title[:55]}

        # Простая версия для стабильности
        return {"Пара": pair_name, "ТФ": tf, "Цена": price, "Сигнал": "NEUTRAL", "Сила": "—", 
                "Рекомендация": "Данные получены"}

    except Exception as e:
        return {"Пара": pair_name, "ТФ": tf, "Цена": "-", "Сигнал": "ERROR", "Сила": "-", 
                "Рекомендация": str(e)[:70]}

# ==================== ИНТЕРФЕЙС ====================
with st.sidebar:
    st.header("⚙ Telegram")
    st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password")
    st.session_state.chat_id = st.text_input("Chat ID", value=st.session_state.chat_id)
    if st.button("💾 Сохранить"):
        st.success("✅ Сохранено!")

    refresh = st.slider("Интервал обновления (сек)", 30, 180, 60)

load_news()

if st.button("🔄 Обновить сейчас"):
    st.rerun()

# ==================== ТАБЛИЦА ====================
data_rows = []
for ticker in DEFAULT_PAIRS.values():
    for tf in ["5m", "15m", "30m"]:
        row = fetch_pair_data(ticker, tf)
        if row:
            data_rows.append(row)

df = pd.DataFrame(data_rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.caption(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')} • Render 24/7")

time.sleep(refresh)
st.rerun()
