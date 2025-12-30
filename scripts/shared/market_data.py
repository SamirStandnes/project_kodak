import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
from scripts.shared.db import get_connection, execute_batch, execute_query

def get_latest_prices(instrument_ids: List[int]) -> Dict[int, Tuple[float, str]]:
    """
    Fetches latest price. Returns {id: (price, currency)}.
    """
    conn = get_connection()
    placeholders = ','.join(['?'] * len(instrument_ids))
    
    # Get Symbol AND Currency from Instruments
    query = f"SELECT id, symbol, currency FROM instruments WHERE id IN ({placeholders})"
    rows = execute_query(query, tuple(instrument_ids))
    
    id_map = {row['symbol']: {'id': row['id'], 'currency': row['currency']} for row in rows if row['symbol']}
    symbols = list(id_map.keys())
    
    if not symbols:
        return {}

    print(f"Fetching prices for {len(symbols)} symbols...")
    try:
        data = yf.download(symbols, period="5d", progress=False)['Close']
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {}

    results = {}
    
    # Helper to safe get
    def get_val(sym):
        if isinstance(data, pd.Series):
             return float(data.dropna().iloc[-1]) if not data.dropna().empty else 0.0
        if sym in data.columns:
             series = data[sym].dropna()
             if not series.empty:
                 return float(series.iloc[-1])
        return 0.0

    for symbol in symbols:
        price = get_val(symbol)
        if price > 0:
            meta = id_map[symbol]
            # Use the currency from our DB, as Yahoo doesn't reliably return it in simple download
            results[meta['id']] = (price, meta['currency'])

    return results

def store_prices(prices: Dict[int, Tuple[float, str]], date_str: str = None):
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
        
    data_to_insert = []
    for inst_id, (price, currency) in prices.items():
        data_to_insert.append((inst_id, date_str, price, currency, 'yfinance'))
        
    execute_batch('''
        INSERT OR REPLACE INTO market_prices (instrument_id, date, close, currency, source)
        VALUES (?, ?, ?, ?, ?)
    ''', data_to_insert)
    print(f"Stored {len(data_to_insert)} prices.")

def get_exchange_rate(from_curr: str, to_curr: str) -> float:
    """
    Fetches the current exchange rate from Yahoo Finance.
    """
    if not from_curr or not to_curr or from_curr == to_curr:
        return 1.0
        
    pair = f"{from_curr}{to_curr}=X"
    try:
        ticker = yf.Ticker(pair)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
        
    # Fallback to common crosses if needed or log error
    print(f"Warning: Could not fetch rate for {pair}. Using 1.0")
    return 1.0