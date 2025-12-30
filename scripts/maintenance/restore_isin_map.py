import sqlite3
import pandas as pd
import os

OLD_DB = 'database/portfolio_old.db'
NEW_DB = 'database/portfolio.db'

def restore_isin_map():
    if not os.path.exists(OLD_DB):
        print(f"Old database not found at {OLD_DB}")
        return

    # 1. Read Old Map
    conn_old = sqlite3.connect(OLD_DB)
    df_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn_old)
    conn_old.close()
    
    print(f"Loaded {len(df_map)} mappings from old DB.")

    # 2. Update New DB
    conn_new = sqlite3.connect(NEW_DB)
    c = conn_new.cursor()
    
    # Add columns if missing
    columns = [row[1] for row in c.execute("PRAGMA table_info(instruments)")]
    new_cols = ['sector', 'region', 'country', 'asset_class']
    
    for col in new_cols:
        if col not in columns:
            print(f"Adding column: {col}")
            c.execute(f"ALTER TABLE instruments ADD COLUMN {col} TEXT")

    # Update Loop
    updated_count = 0
    for _, row in df_map.iterrows():
        isin = row['ISIN']
        symbol = row['Symbol']
        
        # Map old columns to new schema
        # Old: Currency, Sector, Region, Country, (InstrumentType?)
        # Note: InstrumentType might be 'Equity', 'ETF' etc. Check if it exists in old df
        
        asset_class = row.get('InstrumentType') # Might be None if column didn't exist in very old version
        if not asset_class and 'InstrumentType' in df_map.columns:
             asset_class = row['InstrumentType']

        c.execute('''
            UPDATE instruments 
            SET symbol = ?, 
                currency = ?,
                sector = ?, 
                region = ?, 
                country = ?,
                asset_class = ?
            WHERE isin = ?
        ''', (
            symbol, 
            row.get('Currency'),
            row.get('Sector'), 
            row.get('Region'), 
            row.get('Country'), 
            asset_class,
            isin
        ))
        if c.rowcount > 0:
            updated_count += 1
            
    conn_new.commit()
    conn_new.close()
    print(f"Updated {updated_count} instruments with restored metadata.")

if __name__ == '__main__':
    restore_isin_map()
