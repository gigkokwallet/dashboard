import ccxt
import pandas as pd
import ta
import streamlit as st
import requests
import time

# === Streamlit UI Setup ===
st.set_page_config(layout="wide", page_title="📊 Crypto Signal Dashboard")
st.title("📈 Real-Time Crypto Signal Dashboard")
st.caption("Powered by ccxt + ta + Streamlit | By Naseeb")

# === Telegram Config ===
TELEGRAM_TOKEN = '8056034086:AAFB1uDF0lJ6jQDmcVnPVtnMd8vAgsftrbc'
TELEGRAM_CHAT_ID = '5755908955'

def send_telegram_alert(symbol, signal, price, volume_note, status):
    message = f"""🚨 Confirmed Signal Alert
🪙 Symbol: {symbol}
📈 Signal: {signal}
💰 Price: {price:,.4f}
📉 Volume: {volume_note}
📊 Status: {status}
"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

# === Symbol List ===
symbols = [
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'SOL/USDT', 'INJ/USDT',
    'DOGE/USDT', 'WIF/USDT', 'ADA/USDT', 'LINK/USDT', 'AVAX/USDT', 'TIA/USDT',
    'XLM/USDT', 'SUI/USDT', 'BCH/USDT', 'LTC/USDT', 'DOT/USDT', 'UNI/USDT',
    'POPCAT/USDT', 'NEAR/USDT', 'TON/USDT', 'ARB/USDT'
]

# === Settings ===
timeframes = {'main': '5m', 'confirm': '15m'}
limit = 100
exchange = ccxt.mexc()

# === Clear Cache Button ===
if st.button("🧹 Clear Cache"):
    st.cache_data.clear()
    st.experimental_rerun()

# === Fetch OHLCV (with Cache) ===
@st.cache_data(ttl=60)
def get_data(symbol, tf, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# === Indicator Calculation ===
def analyze(df):
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    return df

# === Signal Detection (Only on 5m) ===
def detect_signal(df):
    try:
        macd_cross_up = df['macd'].iloc[-2] < df['macd_signal'].iloc[-2] and df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        macd_cross_down = df['macd'].iloc[-2] > df['macd_signal'].iloc[-2] and df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]

        stoch_cross_up = df['stoch_k'].iloc[-2] < df['stoch_d'].iloc[-2] and df['stoch_k'].iloc[-1] > df['stoch_d'].iloc[-1]
        stoch_cross_down = df['stoch_k'].iloc[-2] > df['stoch_d'].iloc[-2] and df['stoch_k'].iloc[-1] < df['stoch_d'].iloc[-1]

        if macd_cross_up and stoch_cross_up:
            return 'LONG'
        elif macd_cross_down and stoch_cross_down:
            return 'SHORT'
        else:
            return None
    except:
        return None

# === Volume Strength ===
def volume_strength(df):
    v_now = df['volume'].iloc[-1]
    v_avg = df['volume_ma'].iloc[-1]
    if v_now > v_avg * 1.5:
        return "จริง ✅"
    elif v_now < v_avg * 0.5:
        return "หลอก ❗"
    else:
        return "ปกติ 🔄"

# === Confirm Signal by Volume ===
def confirm_signal_by_volume(df_main, df_confirm):
    vol_main = volume_strength(df_main)
    vol_confirm = volume_strength(df_confirm)
    return vol_main == "จริง ✅" and vol_confirm == "จริง ✅"

# === Signal Status Explanation ===
def get_status(df):
    macd_now = df['macd'].iloc[-1]
    macd_sig = df['macd_signal'].iloc[-1]
    stoch_k = df['stoch_k'].iloc[-1]
    stoch_d = df['stoch_d'].iloc[-1]

    if macd_now > macd_sig and stoch_k > stoch_d:
        return "กำลังขึ้น ✅"
    elif macd_now < macd_sig and stoch_k < stoch_d:
        return "กำลังลง ❌"
    elif macd_now > macd_sig or stoch_k > stoch_d:
        return "เริ่มอ่อนแรง ⚠️"
    else:
        return "ยังไม่ชัดเจน 🔄"

# === Main Loop ===
results = []

with st.spinner("🔄 Fetching data & analyzing..."):
    for symbol in symbols:
        try:
            df_main = analyze(get_data(symbol, timeframes['main'], limit))
            df_confirm = analyze(get_data(symbol, timeframes['confirm'], limit))

            signal = detect_signal(df_main)
            vol_strength = volume_strength(df_main)
            price = df_main['close'].iloc[-1]
            status = get_status(df_main)

            is_confirmed = confirm_signal_by_volume(df_main, df_confirm) if signal else None

            if is_confirmed:
                send_telegram_alert(symbol, signal, price, vol_strength, status)

            results.append({
                '🪙 Symbol': symbol,
                '📊 Status': status,
                '📈 Signal': f"{'🟢' if signal == 'LONG' else ('🔴' if signal == 'SHORT' else '⚪')} {signal or '—'}",
                '💰 Price': f"{price:,.4f}",
                '📉 Volume': vol_strength,
                '✅ Confirmed (Vol)': '✅' if is_confirmed else ('❌' if is_confirmed == False else '—')
            })
        except Exception as e:
            st.error(f"{symbol} - {str(e)}")

# === Display Results ===
if results:
    df_result = pd.DataFrame(results)
    st.dataframe(df_result, use_container_width=True)
else:
    st.warning("🚫 No data to show.")
