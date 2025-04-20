# breakout_dashboard.py
import ccxt
import pandas as pd
import streamlit as st
import datetime

st.set_page_config(page_title="Breakout Dashboard", layout="wide")

def fetch_ohlcv(symbol, timeframe):
    exchange = ccxt.mexc()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_stochrsi(df, period=14):
    delta = df['close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    min_rsi = rsi.rolling(window=period).min()
    max_rsi = rsi.rolling(window=period).max()
    stochrsi = 100 * (rsi - min_rsi) / (max_rsi - min_rsi)
    df['StochRSI'] = stochrsi
    return df

def classify_stochrsi_status(stochrsi):
    if stochrsi > 95:
        return "แรงมาก"
    elif 40 < stochrsi <= 95:
        return "ยังมีพื้นที่"
    else:
        return "กำลังกลับตัว"

def generate_trade_advice(break_type, stochrsi):
    if break_type == "HIGH":
        if stochrsi > 95:
            return ("ขึ้นแรงมาก", "รอจังหวะกลับตัว 🔴")
        else:
            return ("ขึ้นแรง", "พิจารณา Long 🟢")
    else:  # LOW
        if stochrsi < 20:
            return ("ลงแรงมาก", "รอจังหวะกลับตัว 🟢")
        else:
            return ("ลงแรง", "พิจารณา Short 🔴")

def analyze(symbol, timeframe):
    df = fetch_ohlcv(symbol, timeframe)
    df = calculate_stochrsi(df)
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    stoch = latest['StochRSI']
    status = classify_stochrsi_status(stoch)
    
    if latest['high'] > previous['high'] and latest['volume'] > previous['volume']:
        break_type = "HIGH"
    elif latest['low'] < previous['low'] and latest['volume'] > previous['volume']:
        break_type = "LOW"
    else:
        return None  # ไม่เข้าเงื่อนไข breakout
    
    adv1, adv2 = generate_trade_advice(break_type, stoch)
    
    return {
        "Symbol": symbol,
        "ราคา": latest['close'],
        "Volume": latest['volume'],
        "StochRSI": round(stoch, 2),
        "สถานะ": status,
        "คำแนะนำ": adv1,
        "กลยุทธ์": adv2
    }

# Main dashboard
st.title("🚀 Crypto Breakout Dashboard (15 นาที)")

symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'SOL/USDT', 
           'DOGE/USDT', 'ADA/USDT', 'LINK/USDT', 'AVAX/USDT', 
           'SUI/USDT', 'LTC/USDT', 'DOT/USDT', 'TON/USDT', 'NEAR/USDT']

timeframe = st.selectbox("เลือกระยะเวลา", options=['15m', '1h', '4h'], index=0)
show_raw = st.checkbox("แสดงทั้งหมด แม้ไม่เข้า Breakout", False)

results = []
with st.spinner("กำลังประมวลผล..."):
    for symbol in symbols:
        try:
            result = analyze(symbol, timeframe)
            if result:
                results.append(result)
            elif show_raw:
                df = fetch_ohlcv(symbol, timeframe)
                df = calculate_stochrsi(df)
                latest = df.iloc[-1]
                results.append({
                    "Symbol": symbol,
                    "ราคา": latest['close'],
                    "Volume": latest['volume'],
                    "StochRSI": round(latest['StochRSI'], 2),
                    "สถานะ": classify_stochrsi_status(latest['StochRSI']),
                    "คำแนะนำ": "-", "กลยุทธ์": "-"
                })
        except Exception as e:
            st.error(f"❌ {symbol} : {e}")

if results:
    df_result = pd.DataFrame(results)
    sort_by = st.selectbox("เรียงตาม", df_result.columns.tolist(), index=2)
    ascending = st.radio("ทิศทางการเรียง", ["มาก -> น้อย", "น้อย -> มาก"]) == "น้อย -> มาก"
    df_result = df_result.sort_values(by=sort_by, ascending=ascending)
    st.dataframe(df_result, use_container_width=True)
else:
    st.warning("ไม่มีข้อมูลที่เข้าเงื่อนไข Breakout")
