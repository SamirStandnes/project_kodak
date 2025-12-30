import sqlite3
import pandas as pd

def export_manual_dnb():
    conn = sqlite3.connect('database/portfolio.db')
    # Let's check for 'DNB' or 'DNB-fix' specifically if possible
    # Based on memory, these were manual entries. 
    # Let's look for rows where Source might be 'Manual' or contains 'DNB'
    query = "SELECT * FROM transactions WHERE Source LIKE '%DNB%' OR Symbol LIKE '%DNB%'"
    df = pd.read_sql_query(query, conn)
    print(f"Exporting {len(df)} DNB-related transactions.")
    df.to_csv('data/new_raw_transactions/manual_dnb_export.csv', index=False)
    conn.close()

if __name__ == '__main__':
    export_manual_dnb()
