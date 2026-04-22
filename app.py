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

# ==================== ИНДИКАТОРЫ (все функции) ====================
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
    plus_dm = [max(highs[i]-highs[i-1], 0) if highs[i]-highs[i-1] > lows[i-1]-lows[i] else 0 for i in range(1, len(highs))]
    minus_dm = [max(lows[i-1]-lows[i], 0) if lows[i-1]-lows[i] > highs[i]-highs[i-1] else 0 for i in range(1, len(highs))]
    plus_di = 100 * (sum(plus_dm[-period:]) / period) / atr if atr != 0 else 0
    minus_di = 100 * (sum(minus_dm[-period:]) / period) / atr if atr != 0 else 0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001) * 100
    return dx

def calculate_bollinger(closes, period=20, std_mult=2):
    if len(closes) < period: return closes[-1], closes[-1], closes[-1]
    sma = sum(closes[-period:]) / period
    std = (sum((x - sma)**2 for x in closes[-period:]) / period) ** 0.5
    return sma, sma + std_mult*std, sma - std_mult*std

def fetch_pair_data(ticker, tf):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={tf}&range=10d"
        data = requests.get(url, timeout=12).json()
        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        closes = quotes["close"][-350:]
        highs = quotes["high"][-350:]
        lows = quotes["low"][-350:]
        if len(closes) < 200: return None

        price = round(closes[-1], 4)
        pair_name = next((k for k, v in DEFAULT_PAIRS.items() if v == ticker), ticker.replace("=X","").replace("=F",""))

        has_news, news_title = has_high_impact_news(pair_name)
        if has_news:
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "Сигнал": "🟥 BLOCKED", "Сила": "NEWS", "Рекомендация": news_title[:60]}

        rsi = calculate_rsi(closes)
        macd_line, sig_line = calculate_macd_lines(closes)
        macd_cross_bull = macd_line[-2] <= sig_line[-2] and macd_line[-1] > sig_line[-1]
        macd_cross_bear = macd_line[-2] >= sig_line[-2] and macd_line[-1] < sig_line[-1]

        ema200 = calculate_ema(closes, 200)[-1]
        trend_up = closes[-1] > ema200
        trend_down = closes[-1] < ema200

        stoch_k, stoch_d, stoch_prev = calculate_stochastic(highs, lows, closes)
        stoch_oversold = stoch_k < 22 and stoch_d < 22
        stoch_overbought = stoch_k > 78 and stoch_d > 78
        stoch_cross_up = stoch_prev <= stoch_d and stoch_k > stoch_d

        adx = calculate_adx(highs, lows, closes)
        _, bb_up, bb_low = calculate_bollinger(closes)
        bb_pos = "Lower" if price <= bb_low*1.001 else "Upper" if price >= bb_up*0.999 else "Middle"

        strong_call = rsi < 30 and macd_cross_bull and trend_up and stoch_oversold and stoch_cross_up and adx > 22 and bb_pos == "Lower"
        strong_put = rsi > 70 and macd_cross_bear and trend_down and stoch_overbought and adx > 22 and bb_pos == "Upper"

        if strong_call:
            send_telegram(f"🔥 <b>MAX CALL</b> {pair_name} {tf}\nЦена: {price} | ADX: {adx:.1f}")
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "RSI": round(rsi,1), "ADX": round(adx,1), "BB": bb_pos, "Сигнал": "✅ CALL", "Сила": "MAX", "Рекомендация": "Открывай CALL 3-5 мин"}
        elif strong_put:
            send_telegram(f"🔥 <b>MAX PUT</b> {pair_name} {tf}\nЦена: {price} | ADX: {adx:.1f}")
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "RSI": round(rsi,1), "ADX": round(adx,1), "BB": bb_pos, "Сигнал": "❌ PUT", "Сила": "MAX", "Рекомендация": "Открывай PUT 3-5 мин"}
        else:
            return {"Пара": pair_name, "ТФ": tf, "Цена": price, "RSI": round(rsi,1), "ADX": round(adx,1), "BB": bb_pos, "Сигнал": "NEUTRAL", "Сила": "—", "Рекомендация": "Жди"}
    except:
        return {"Пара": pair_name, "ТФ": tf, "Цена": "-", "Сигнал": "ERROR", "Сила": "-", "Рекомендация": "Ошибка загрузки"}

# ==================== ИНТЕРФЕЙС ====================
with st.sidebar:
    st.header("⚙ Telegram")
    st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password")
    st.session_state.chat_id = st.text_input("Chat ID", value=st.session_state.chat_id)
    if st.button("Сохранить настройки"):
        st.success("✅ Сохранено")

    st.header("🔄 Обновление")
    refresh = st.slider("Интервал (сек)", 30, 120, 45)

load_news()

if st.button("🔄 Обновить сейчас"):
    st.rerun()

# Основная таблица
data_rows = []
for name, ticker in DEFAULT_PAIRS.items():
    for tf in ["5m", "15m", "30m"]:
        row = fetch_pair_data(ticker, tf)
        if row:
            data_rows.append(row)

df = pd.DataFrame(data_rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.caption(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')} • Работает 24/7 на Render")

# Автообновление
time.sleep(refresh)
st.rerun()
