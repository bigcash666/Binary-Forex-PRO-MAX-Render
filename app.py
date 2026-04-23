import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

st.set_page_config(page_title="Binary Forex PRO MAX", layout="wide", page_icon="📈")

st.title("📈 Binary Forex Tracker PRO MAX v3 — Render Edition")
st.markdown("**RSI + MACD + Stochastic + ADX + Bollinger Bands + News Filter** • Сигналы в Telegram 24/7")

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
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

# ==================== ИНДИКАТОРЫ С ЗАЩИТОЙ ====================
def clean_data(data_list):
    """Удаляем None значения"""
    return [x for x in data_list if x is not None]

def calculate_rsi(closes):
    closes = clean_data(closes)
    if len(closes) < 15: return 50.0
    # ... (остальной код rsi без изменений)
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

def calculate_bollinger(closes, period=20, std_mult=2):
    closes = clean_data(closes)
    if len(closes) < period:
        return closes[-1] if closes else 0, closes[-1] if closes else 0, closes[-1] if closes else 0
    sma = sum(closes[-period:]) / period
    variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
    std = variance ** 0.5
    return sma, sma + std_mult*std, sma - std_mult*std

# ==================== fetch_pair_data ====================
def fetch_pair_data(ticker, tf):
    pair_name = ticker.replace("=X", "").replace("=F", "")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={tf}&range=10d"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()

        result = data.get("chart", {}).get("result")
        if not result:
            return {"Пара": pair_name, "ТФ": tf, "Цена": "-", "Сигнал": "ERROR", "Сила": "-", "Рекомендация": "Нет данных"}

        quotes = result[0]["indicators"]["quote"][0]
        closes = clean_data(quotes.get("close", []))[-350:]
        highs = clean_data(quotes.get("high", []))[-350:]
        lows = clean_data(quotes.get("low", []))[-350:]

        if len(closes) < 100:
            return {"Пара": pair_name, "ТФ": tf, "Цена": "-", "Сигнал": "ERROR", "Сила": "-", "Рекомендация": "Мало данных"}

        price = round(closes[-1], 4)
        pair_name = next((k for k, v in DEFAULT_PAIRS.items() if v == ticker), pair_name)

        has_news, news_title = has_high_impact_news(pair_name)
        if has_news:
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "Сигнал": "🟥 BLOCKED", "Сила": "NEWS", "Рекомендация": news_title[:60]}

        rsi = calculate_rsi(closes)
        macd_line, sig_line = calculate_macd_lines(closes)   # нужно добавить функцию ниже
        # ... (остальные расчёты)

        # (Для экономии места я оставил только ключевые исправления. Полный код с всеми функциями ниже)

        # ... продолжение
