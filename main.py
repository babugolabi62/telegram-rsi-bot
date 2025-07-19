import requests
import pandas as pd
import time
import json
import threading
from datetime import datetime
import pytz
from flask import Flask
import ta

# === Flask-приложение ===
app = Flask(__name__)

# === Загрузка конфигурации ===
with open("config.json", "r") as f:
    config = json.load(f)

TELEGRAM_TOKEN = config["telegram_token"]
TELEGRAM_CHAT_ID = config["telegram_chat_id"]

symbols = ["BTCUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT"]
intervals = ["1d", "1h", "15m", "5m"]
rsi_period = 14
atr_period = 14

kyiv_tz = pytz.timezone("Europe/Kyiv")

# === Отправка сообщений в Telegram ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# === Получение свечей с Binance ===
def get_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if not data:
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

# === RSI ===
def calculate_rsi(df, period=rsi_period):
    try:
        return round(ta.momentum.RSIIndicator(df['close'], window=period).rsi().iloc[-1], 2)
    except:
        return None

# === ATR % ===
def calculate_atr_percent(df, period=atr_period):
    try:
        atr = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=period
        ).average_true_range()
        price = df['close'].iloc[-1]
        return round((atr.iloc[-1] / price) * 100, 2)
    except:
        return None

# === Текущая цена ===
def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url, timeout=5)
        return round(float(response.json()["price"]), 4)
    except:
        return "n/a"

# === Основной цикл мониторинга ===
def rsi_monitor_loop():
    while True:
        now = datetime.now(kyiv_tz).strftime("%Y-%m-%d %H:%M")
        message = f"📊 *Мониторинг RSI & ATR%*\n🕒 Время: `{now} (Kyiv)`\n\n"

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
        print(f"[{now}] Отправлено в Telegram. Ждём 15 минут...")
        time.sleep(15 * 60)

# === Запуск потока мониторинга при старте Flask ===
@app.route('/')
def index():
    return "Telegram RSI & ATR% бот запущен. Работает в фоне."

if __name__ == '__main__':
    threading.Thread(target=rsi_monitor_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
