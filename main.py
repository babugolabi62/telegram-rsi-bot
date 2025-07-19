import requests
import pandas as pd
import time
import json
from datetime import datetime
import ta

# === Загрузка конфигурации ===
with open("config.json", "r") as f:
    config = json.load(f)

TELEGRAM_TOKEN = config["telegram_token"]
TELEGRAM_CHAT_ID = config["telegram_chat_id"]

symbols = ["BTCUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT"]
intervals = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "1d": "1d"
}
rsi_period = 14
atr_period = 14

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def get_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if not data:
            print(f"Пустой список свечей для {symbol} {interval}")
            return None
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        return df
    except Exception as e:
        print(f"Ошибка получения данных {symbol} {interval}: {e}")
        return None

def calculate_rsi(df, period=rsi_period):
    try:
        return round(ta.momentum.RSIIndicator(df['close'], window=period).rsi().iloc[-1], 2)
    except:
        return None

def calculate_atr_percent(df, period=atr_period):
    try:
        atr = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=period
        ).average_true_range()
        price = df['close'].iloc[-1]
        return round((atr.iloc[-1] / price) * 100, 2)
    except:
        return None

def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url, timeout=5)
        return round(float(response.json()["price"]), 4)
    except:
        return "n/a"

while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"📊 *Мониторинг RSI & ATR%*\n🕒 Время: `{now}`\n\n"

    for symbol in symbols:
        price = get_current_price(symbol)
        message += f"🔸 *{symbol}* | 💰 *{price} $*\n"
        message += "───────────────\n"
        for interval in intervals:
            df = get_klines(symbol, interval)
            if df is not None:
                rsi = calculate_rsi(df)
                atr = calculate_atr_percent(df)
                rsi_str = f"{rsi}" if rsi is not None else "n/a"
                atr_str = f"{atr}%" if atr is not None else "n/a"
                message += f"🕐 {interval:<4} | RSI: {rsi_str:<5} | ATR: {atr_str}\n"
            else:
                message += f"🕐 {interval:<4} | ❌ Ошибка загрузки\n"
        message += "\n"

    send_telegram_message(message)
    print(f"[{datetime.now()}] Сообщение отправлено. Ожидание 15 минут...")
    time.sleep(15 * 60)

