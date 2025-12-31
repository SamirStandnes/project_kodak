import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from scripts.shared.db import get_connection

def enrich_staging_data():
    conn = get_connection()
    
    # 1. Enrich Main Transaction FX
    # Enrich if rate is missing OR if local amount is missing OR if local amount equals amount (unconverted)
    df_tx = pd.read_sql("SELECT * FROM transactions WHERE (exchange_rate = 0.0 OR amount_local = 0.0 OR abs(amount_local - amount) < 0.01) AND amount != 0.0 AND currency != 'NOK'", conn)
    
    updates_tx = []
    # Cache to avoid duplicate requests for same date/pair
    cache = {}

    if not df_tx.empty:
        print(f"Enriching {len(df_tx)} transactions with historical FX rates...")
        for idx, row in df_tx.iterrows():
            curr = row['currency']
            date_str = row['date'].split(' ')[0] # YYYY-MM-DD
            rate = row['exchange_rate']

            # If we already have a rate, just use it to fix amount_local
            if rate > 0:
                pass 
            else:
                rate = _get_rate(curr, date_str, cache)
            
            if rate > 0:
                # Update amount_local
                new_amount_local = row['amount'] * rate
                updates_tx.append((rate, new_amount_local, row['external_id']))

        if updates_tx:
            c = conn.cursor()
            c.executemany("UPDATE transactions SET exchange_rate = ?, amount_local = ? WHERE external_id = ?", updates_tx)
            conn.commit()
            print(f"Updated {len(updates_tx)} transactions with historical rates.")
            
    # 2. Enrich Fee FX
    # Enrich where fee is non-zero but fee_local is 0 (meaning we couldn't convert it during parse)
    df_fee = pd.read_sql("SELECT * FROM transactions WHERE fee != 0 AND fee_local = 0 AND fee_currency != 'NOK'", conn)
    
    updates_fee = []
    if not df_fee.empty:
        print(f"Enriching {len(df_fee)} fees with historical FX rates...")
        for idx, row in df_fee.iterrows():
            curr = row['fee_currency']
            date_str = row['date'].split(' ')[0]
            
            # Try to use the main transaction rate if currencies match
            rate = 0.0
            if row['currency'] == curr and row['exchange_rate'] > 0:
                rate = row['exchange_rate']
            else:
                rate = _get_rate(curr, date_str, cache)
            
            if rate > 0:
                new_fee_local = row['fee'] * rate
                updates_fee.append((new_fee_local, row['external_id']))
                
        if updates_fee:
            c = conn.cursor()
            c.executemany("UPDATE transactions SET fee_local = ? WHERE external_id = ?", updates_fee)
            conn.commit()
            print(f"Updated {len(updates_fee)} fees with historical rates.")

    conn.close()

def _get_rate(currency, date_str, cache):
    cache_key = f"{currency}_{date_str}"
    if cache_key in cache:
        return cache[cache_key]
    
    pair = f"{currency}NOK=X"
    print(f"Fetching {pair} for {date_str}...")
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        end_d = d + timedelta(days=3)
        ticker = yf.Ticker(pair)
        hist = ticker.history(start=date_str, end=end_d.strftime('%Y-%m-%d'), interval='1d')
        
        if not hist.empty:
            rate = float(hist['Close'].iloc[0])
            cache[cache_key] = rate
            return rate
    except Exception as e:
        print(f"Error fetching {pair}: {e}")
    
    return 0.0

if __name__ == '__main__':
    enrich_staging_data()
