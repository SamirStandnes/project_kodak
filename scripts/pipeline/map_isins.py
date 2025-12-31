import pandas as pd
import os
from scripts.shared.db import get_connection

ISIN_MAP_PATH = os.path.join('data', 'reference', 'isin_map.csv')

def map_isins():
    if not os.path.exists(ISIN_MAP_PATH):
        print(f"ISIN map not found at {ISIN_MAP_PATH}")
        return

    print("Loading ISIN map...")
    df_map = pd.read_csv(ISIN_MAP_PATH)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = 0
    for _, row in df_map.iterrows():
        isin = row['ISIN']
        symbol = row['Symbol']
        currency = row['Currency']
        
        # Update instrument
        cursor.execute("""
            UPDATE instruments 
            SET symbol = ?, currency = ?
            WHERE isin = ?
        """, (symbol, currency, isin))
        
        if cursor.rowcount > 0:
            updates += cursor.rowcount
            
    conn.commit()
    conn.close()
    print(f"Updated {updates} instruments based on ISIN map.")

if __name__ == "__main__":
    map_isins()
