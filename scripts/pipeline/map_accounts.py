import sys
from pathlib import Path
import pandas as pd
import os

# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from scripts.shared.db import get_connection

ACCOUNTS_MAP_PATH = os.path.join('data', 'reference', 'accounts.csv')

def map_accounts():
    if not os.path.exists(ACCOUNTS_MAP_PATH):
        print(f"Accounts map not found at {ACCOUNTS_MAP_PATH}")
        return

    print("Loading Accounts map...")
    df_map = pd.read_csv(ACCOUNTS_MAP_PATH)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = 0
    for _, row in df_map.iterrows():
        ext_id = str(row['external_id'])
        name = row['name']
        broker = row.get('broker')
        acc_type = row.get('type')
        
        # Update account
        cursor.execute("""
            UPDATE accounts 
            SET name = ?, broker = ?, type = ?
            WHERE external_id = ?
        """, (name, broker, acc_type, ext_id))
        
        if cursor.rowcount > 0:
            updates += cursor.rowcount
            
    conn.commit()
    conn.close()
    print(f"Updated {updates} accounts based on accounts.csv.")

if __name__ == "__main__":
    map_accounts()
