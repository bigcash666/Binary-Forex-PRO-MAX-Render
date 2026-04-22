import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone
import os

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

# ==================== ДОПОЛНИТЕЛЬНЫЕ ИНДИКАТОРЫ ====================
def calculate_rsi(closes):
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
    if len(data) < period: return [data[0]] * len(data)
    k = 2 / (period + 1)
    ema = [data[0]]
    for i in range(1, len(data)):
        ema.append(data[i] * k + ema[i-1] * (1 - k))
    return ema

def calculate_macd_lines(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(ema12))]
    signal_line = calculate_ema(macd_line, 9)
    return macd_line, signal_line

def calculate_stochastic(highs, lows, closes):
    if len(closes) < 20: return 50, 50, 50
    k_values = []
    for i in range(13, len(closes)):
        ll = min(lows[i-13:i+1])
        hh = max(highs[i-13:i+1])
        k = 100 * (closes[i] - ll) / (hh - ll) if hh != ll else 50
        k_values.append(k)
    k_smooth = sum(k_values[-3:]) / 3
    d = sum(k_values[-6:-3]) / 3 if len(k_values) > 5 else k_smooth
    return k_smooth, d, k_values[-4] if len(k_values) > 3 else k_smooth

def calculate_adx(highs, lows, closes, period=14):
    if len(highs) < period + 10: return 20.0
    tr = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(highs))]
    atr = sum(tr[-period:]) / period
    plus... # Продолжайте сюда дальше ваши индикаторы
    # здесь пример, дальше можно дополнять по вашим needs


# ==================== ВАША ОСНОВНАЯ ЛОГИКА ====================
def fetch_pair_data(ticker, tf):
    # Объявляем pair_name с дефолтным значением перед try
    pair_name = next((k for k, v in DEFAULT_PAIRS.items() if v == ticker), ticker.replace("=X","").replace("=F",""))
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={tf}&range=10d"
        data = requests.get(url, timeout=12).json()
        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        closes = quotes["close"][-350:]
        highs = quotes["high"][-350:]
        lows = quotes["low"][-350:]

        # Проверка наличия данных
        if len(closes) == 0:
            return None

        # Проверка новостей
        has_news, news_title = has_high_impact_news(pair_name)
        if has_news:
            return {"Пара": pair_name, "Новости": news_title}
        # Можно добавить сюда расчет индикаторов и дальнейший анализ

    except Exception as e:
        # Логирование ошибок, по желанию
        # print(f"Error fetching data for {ticker}: {e}")
        pass

    return None

# ==================== ВЫПОЛНЕНИЕ ====================
# например, сегодня вызовем для пары EUR/USD
result = fetch_pair_data(DEFAULT_PAIRS["EUR/USD"], "15m")
if result:
    st.write(result)
