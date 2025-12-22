# scripts/analysis/utils.py

from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import sys

data_cache = {}

def parse_date_flexible(date_string):
    """
    Parses a date string that could be in one of several formats.
    """
    if not date_string:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None

def get_historical_price(ticker_symbol, date):
    """
    Fetches the closing price for a given ticker symbol on a specific date.
    Includes a 7-day lookback for resilience against non-trading days.
    """
    cache_key = f"{ticker_symbol}-{date.strftime('%Y-%m-%d')}"
    if cache_key in data_cache:
        return data_cache[cache_key]

    try:
        # Look back a few days to find the last available closing price
        end_date = pd.to_datetime(date) + timedelta(days=1)
        start_date = end_date - timedelta(days=14) 
        
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=False, back_adjust=False)
        
        if hist.empty:
            data_cache[cache_key] = None
            return None
            
        # Use the last available price in the window
        price = hist['Close'].iloc[-1]
        data_cache[cache_key] = price
        return price
    except Exception as e:
        print(f"Warning: Could not get price for {ticker_symbol} on {date.strftime('%Y-%m-%d')}: {e}", file=sys.stderr)
        data_cache[cache_key] = None
        return None

def get_historical_exchange_rate(base_currency, target_currency, date):
    """
    Fetches the historical exchange rate between two currencies for a specific date.
    """
    if base_currency == target_currency:
        return 1.0

    # yfinance uses specific ticker formats for currencies
    ticker_symbol = f"{base_currency}{target_currency}=X"
    
    # Use the historical price function to get the exchange rate
    rate = get_historical_price(ticker_symbol, date)
    return rate

