import sqlite3
import pandas as pd

def restore_isin_map():
    conn = sqlite3.connect('database/portfolio.db')
    
    # 1. Load from the reference CSV
    try:
        df = pd.read_csv('data/reference/isin_map.csv')
        # Only take what we have
        cols = [c for f in ['ISIN', 'Symbol', 'Currency'] if (c := f) in df.columns]
        map_df = df[cols].drop_duplicates('ISIN')
        
        map_df.to_sql('isin_symbol_map', conn, if_exists='append', index=False)
        print(f"Restored {len(map_df)} entries to isin_symbol_map.")
    except Exception as e:
        print(f"Failed to restore from CSV: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    restore_isin_map()
