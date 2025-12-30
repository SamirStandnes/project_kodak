import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
from .db import get_db_connection

# Caches
exchange_rates_cache = {}
price_cache = {}

def get_current_prices_from_db(conn=None):
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    try:
        df = pd.read_sql_query("SELECT ISIN, Price FROM current_prices", conn)
        return df.set_index('ISIN')['Price'].to_dict()
    finally:
        if should_close: conn.close()

def get_historical_price(ticker_symbol, date, isin=None, conn=None):
    date_str = date.strftime('%Y-%m-%d')
    if isin and conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Price FROM historical_price_overrides WHERE ISIN = ? AND Date = ?", (isin, date_str))
            row = cursor.fetchone()
            if row: return row[0]
        except Exception: pass

    cache_key = f"{ticker_symbol}-{date_str}"
    if cache_key in price_cache: return price_cache[cache_key]
    try:
        end_date = pd.to_datetime(date) + timedelta(days=1)
        start_date = end_date - timedelta(days=14) 
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=False, back_adjust=False)
        if hist.empty:
            price_cache[cache_key] = None
            return None
        price = hist['Close'].iloc[-1]
        price_cache[cache_key] = price
        return price
    except Exception as e:
        price_cache[cache_key] = None
        return None

def get_exchange_rate(base_currency, target_currency='NOK', date=None):
    if not base_currency or base_currency == target_currency: return 1.0
    if base_currency == 'HKD' and target_currency == 'NOK':
        usd_nok = get_exchange_rate('USD', 'NOK', date)
        hkd_usd = get_exchange_rate('HKD', 'USD', date)
        return usd_nok * hkd_usd if usd_nok and hkd_usd else None
    ticker = f"{base_currency}{target_currency}=X"
    date_str = None
    if date:
        if isinstance(date, str): date_str = date.split(' ')[0]
        elif isinstance(date, datetime): date_str = date.strftime('%Y-%m-%d')
    cache_key = f"{ticker}-{date_str}" if date_str else ticker
    if cache_key in exchange_rates_cache: return exchange_rates_cache[cache_key]
    try:
        if date_str:
            start_date = date_str
            end_date_obj = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=1)
            end_date = end_date_obj.strftime('%Y-%m-%d')
            rate_data = yf.Ticker(ticker).history(start=start_date, end=end_date)
        else: rate_data = yf.Ticker(ticker).history(period="1d")
        if not rate_data.empty:
            rate = rate_data['Close'].iloc[-1]
            exchange_rates_cache[cache_key] = rate
            return rate
        elif date_str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            for i in range(1, 5):
                prev_date = (dt - timedelta(days=i)).strftime('%Y-%m-%d')
                rate = get_exchange_rate(base_currency, target_currency, prev_date)
                if rate: return rate
        return None
    except Exception: return None