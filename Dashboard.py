import ccxt
import pandas as pd
import ta
import streamlit as st
import time
import requests

# === Telegram Config ===
TELEGRAM_TOKEN = '8056034086:AAFB1uDF0lJ6jQDmcVnPVtnMd8vAgsftrbc'
TELEGRAM_CHAT_ID = '5755908955'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

# === UI Setup ===
st.set_page_config(layout="wide", page_title="📊 Crypto Signal Dashboard")
st.title("📈 Real-Time Crypto Signal Dashboard")
st.caption("Powered by ccxt + ta + Streamlit | By Naseeb")

# === Sidebar Filters ===
st.sidebar.markdown("## 🔍 Filter Options")
signal_filter = st.sidebar.selectbox("เลือกประเภทสัญญาณ", ["ทั้งหมด", "LONG", "SHORT"])
volume_filter = st.sidebar.checkbox("แสดงเฉพาะที่ Confirmed Volume ✅", value=False)

# === Symbol list ===
symbols = [
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'SOL/USDT', 'INJ/USDT',
    'DOGE/USDT', 'WIF/USDT', 'ADA/USDT', 'LINK/USDT', 'AVAX/USDT', 'TIA/USDT',
    'XLM/USDT', 'SUI/USDT', 'BCH/USDT', 'LTC/USDT', 'DOT/USDT', 'PI/USDT',
    'POPCAT/USDT', 'UNI/USDT', 'ONDO/USDT', 'TON/USDT', 'ARB/USDT', 'NEAR/USDT', 
    'TRUMP/USDT', 'ENA/USDT'
]

# === Settings ===
timeframes = {'main': '5m', 'confirm': '15m'}
limit = 100
exchange = ccxt.mexc()

# === Clear cache button ===
if st.button("🧹 Clear Cache"):
    st.cache_data.clear()
    st.experimental_rerun()

# === Cached OHLCV Fetching ===
@st.cache_data(ttl=60)
def get_data(symbol, tf, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# === Technical Analysis ===
def analyze(df):
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    return df

# === Signal Detection ===
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

# === Volume Confirmation ===
def confirm_volume(df_main, df_confirm):
    vol_now_main = df_main['volume'].iloc[-1]
    vol_ma_main = df_main['volume_ma'].iloc[-1]

    vol_now_conf = df_confirm['volume'].iloc[-1]
    vol_ma_conf = df_confirm['volume_ma'].iloc[-1]

    return vol_now_main > vol_ma_main * 1.5 and vol_now_conf > vol_ma_conf * 1.5

# === Status ===
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

# === Styling ===
def color_signal(val):
    if "LONG" in val:
        return 'background-color: #c6f6d5'
    elif "SHORT" in val:
        return 'background-color: #fed7d7'
    return ''

def color_confirm(val):
    if val == '✅':
        return 'background-color: #9ae6b4'
    elif val == '❌':
        return 'background-color: #feb2b2'
    return ''

# === Run Analysis ===
results = []
with st.spinner("🔄 Fetching data & analyzing..."):
    for symbol in symbols:
        try:
            df_main = analyze(get_data(symbol, timeframes['main'], limit))
            df_confirm = analyze(get_data(symbol, timeframes['confirm'], limit))

            signal = detect_signal(df_main)
            confirmed_vol = confirm_volume(df_main, df_confirm)
            price = df_main['close'].iloc[-1]
            status = get_status(df_main)

            if signal and confirmed_vol:
                send_telegram_message(f"\ud83d\udd39 *{symbol}* | {signal}\n\ud83d\udcc8 ราคา: {price:,.2f}\n\ud83d\udd22 สถานะ: {status}")

            results.append({
                '🪙 Symbol': symbol,
                '📊 Status': status,
                '📈 Signal': f"{'🟢' if signal == 'LONG' else ('🔴' if signal == 'SHORT' else '⚪')} {signal or '—'}",
                '💰 Price': f"{price:,.4f}",
                '✅ Confirmed (Vol)': '✅' if confirmed_vol else '❌'
            })

        except Exception as e:
            st.error(f"{symbol} - {str(e)}")

# === Filter Results ===
df_result = pd.DataFrame(results)
df_filtered = df_result.copy()

if signal_filter != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered['📈 Signal'].str.contains(signal_filter)]
if volume_filter:
    df_filtered = df_filtered[df_filtered['✅ Confirmed (Vol)'] == '✅']

styled_df = df_filtered.style.applymap(color_signal, subset=['📈 Signal'])\
                               .applymap(color_confirm, subset=['✅ Confirmed (Vol)'])

st.dataframe(styled_df, use_container_width=True, height=700)

if df_filtered.empty:
    st.warning("🚫 No data to show.")
