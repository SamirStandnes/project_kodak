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
        isin = row['isin']
        symbol = row['symbol']
        currency = row['currency']
        sector = row.get('sector')
        region = row.get('region')
        country = row.get('country')
        asset_class = row.get('asset_class')
        
        # Update instrument
        cursor.execute("""
            UPDATE instruments 
            SET symbol = ?, 
                currency = ?,
                sector = ?,
                region = ?,
                country = ?,
                asset_class = ?
            WHERE isin = ?
        """, (symbol, currency, sector, region, country, asset_class, isin))
        
        if cursor.rowcount > 0:
            updates += cursor.rowcount
            
    conn.commit()
    conn.close()
    print(f"Updated {updates} instruments based on ISIN map.")

if __name__ == "__main__":
    map_isins()
