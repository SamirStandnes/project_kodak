import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from scripts.shared.db import get_connection

def enrich_staging_fx():
    conn = get_connection()
    # Enrich if rate is missing OR if local amount is missing OR if local amount equals amount (unconverted)
    df = pd.read_sql("SELECT * FROM transactions WHERE (exchange_rate = 0.0 OR amount_local = 0.0 OR abs(amount_local - amount) < 0.01) AND amount != 0.0 AND currency != 'NOK'", conn)
    
    if df.empty:
        print("No transactions requiring FX enrichment.")
        conn.close()
        return

    print(f"Enriching {len(df)} transactions with historical FX rates...")
    
    updates = []
    # Cache to avoid duplicate requests for same date/pair
    cache = {}

    for idx, row in df.iterrows():
        curr = row['currency']
        date_str = row['date'].split(' ')[0] # YYYY-MM-DD
        rate = row['exchange_rate']

        # If we already have a rate, just use it to fix amount_local
        if rate > 0:
            pass 
        else:
            # Need to fetch rate
            cache_key = f"{curr}_{date_str}"
            
            if cache_key in cache:
                rate = cache[cache_key]
            else:
                pair = f"{curr}NOK=X"
            print(f"Fetching {pair} for {date_str}...")
            try:
                # Get historical data for that day
                d = datetime.strptime(date_str, '%Y-%m-%d')
                end_d = d + timedelta(days=3) # buffer
                ticker = yf.Ticker(pair)
                hist = ticker.history(start=date_str, end=end_d.strftime('%Y-%m-%d'), interval='1d')
                
                if not hist.empty:
                    rate = float(hist['Close'].iloc[0])
                    cache[cache_key] = rate
                else:
                    print(f"No rate found for {pair} on {date_str}")
                    rate = 0.0
            except Exception as e:
                print(f"Error fetching {pair}: {e}")
                rate = 0.0
        
        if rate > 0:
            # Update amount_local
            # Note: amount is already negative for BUYs
            new_amount_local = row['amount'] * rate
            updates.append((rate, new_amount_local, row['external_id']))

    if updates:
        c = conn.cursor()
        c.executemany("UPDATE transactions SET exchange_rate = ?, amount_local = ? WHERE external_id = ?", updates)
        conn.commit()
        print(f"Updated {len(updates)} rows with historical rates.")
    
    conn.close()

if __name__ == '__main__':
    enrich_staging_fx()
