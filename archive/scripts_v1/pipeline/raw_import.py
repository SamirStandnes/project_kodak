import pandas as pd
import sqlite3
import os

def process_files():
    raw_path = 'data/new_raw_transactions'
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    
    # 1. Nordnet
    nordnet_file = os.path.join(raw_path, 'transactions-and-notes-export.csv')
    if os.path.exists(nordnet_file):
        df = pd.read_csv(nordnet_file, sep='\t', encoding='utf-16')
        df.to_sql('raw_nordnet', conn, if_exists='replace', index=False)
        print("Imported raw Nordnet table.")

    # 2. Saxo
    for i, f in enumerate([f for f in os.listdir(raw_path) if f.startswith('Transactions')]):
        path = os.path.join(raw_path, f)
        xl = pd.ExcelFile(path)
        sheet = 'Transaksjoner' if 'Transaksjoner' in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(path, sheet_name=sheet)
        df.to_sql(f'raw_saxo_{i}', conn, if_exists='replace', index=False)
        print(f"Imported raw Saxo table: raw_saxo_{i} ({f})")
            
    conn.close()

if __name__ == '__main__':
    process_files()