import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
from .db import get_db_connection

# Caches
exchange_rates_cache = {}
price_cache = {}

def get_current_prices_from_db(conn=None):
    """
    Fetches the latest snapshot of prices from the current_prices table.
    Returns a dictionary {ISIN: Price}.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
        
    try:
        df = pd.read_sql_query("SELECT ISIN, Price FROM current_prices", conn)
        return df.set_index('ISIN')['Price'].to_dict()
    finally:
        if should_close:
            conn.close()

def get_historical_price(ticker_symbol, date):
    """
    Fetches the closing price for a given ticker symbol on a specific date using yfinance.
    Includes a 7-day lookback for resilience against non-trading days.
    """
    date_str = date.strftime('%Y-%m-%d')
    cache_key = f"{ticker_symbol}-{date_str}"
    
    if cache_key in price_cache:
        return price_cache[cache_key]

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
        print(f"Warning: Could not get price for {ticker_symbol} on {date_str}: {e}", file=sys.stderr)
        price_cache[cache_key] = None
        return None

def get_exchange_rate(base_currency, target_currency='NOK', date=None):
    """
    Gets the exchange rate for a given date.
    If date is None, fetches the latest rate (live).
    """
    if not base_currency or base_currency == target_currency:
        return 1.0

    # Handle HKD conversion via USD cross-rate
    if base_currency == 'HKD' and target_currency == 'NOK':
        usd_nok = get_exchange_rate('USD', 'NOK', date)
        hkd_usd = get_exchange_rate('HKD', 'USD', date)
        if usd_nok and hkd_usd:
            return usd_nok * hkd_usd
        else:
            return None

    ticker = f"{base_currency}{target_currency}=X"
    
    # Handle date format
    date_str = None
    if date:
        if isinstance(date, str):
            date_str = date.split(' ')[0]
        elif isinstance(date, datetime):
            date_str = date.strftime('%Y-%m-%d')
            
    cache_key = f"{ticker}-{date_str}" if date_str else ticker

    if cache_key in exchange_rates_cache:
        return exchange_rates_cache[cache_key]

    try:
        if date_str:
            # Historical
            # Reuse get_historical_price logic? No, yfinance ticker format is same but simpler to keep explicit
            start_date = date_str
            end_date_obj = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=1)
            end_date = end_date_obj.strftime('%Y-%m-%d')
            rate_data = yf.Ticker(ticker).history(start=start_date, end=end_date)
        else:
            # Live
            rate_data = yf.Ticker(ticker).history(period="1d")
        
        if not rate_data.empty:
            rate = rate_data['Close'].iloc[-1] # Use last available
            exchange_rates_cache[cache_key] = rate
            return rate
        else:
            # Fallback for historical lookup if empty (weekend)
            if date_str:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                for i in range(1, 5):
                    prev_date = (dt - timedelta(days=i)).strftime('%Y-%m-%d')
                    rate = get_exchange_rate(base_currency, target_currency, prev_date)
                    if rate: 
                        return rate
            return None
            
    except Exception as e:
        print(f"Warning: Error fetching rate for {ticker}: {e}")
        return None

# Alias for compatibility if needed, but we should refactor consumers to use get_exchange_rate
def get_historical_exchange_rate(base_currency, target_currency, date):
    return get_exchange_rate(base_currency, target_currency, date)
