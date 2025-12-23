import sqlite3
import pandas as pd
import hashlib

def generate_txn_hash(row):
    # Create a unique string based on key content
    # Handling None/NaN by converting to string 'None' or 0
    date = str(row['TradeDate']).split(' ')[0] # YYYY-MM-DD
    acct = str(row['AccountID'])
    type_ = str(row['Type'])
    symbol = str(row['Symbol']) if row['Symbol'] else ''
    amount = f"{float(row['Amount_Base']):.2f}" if row['Amount_Base'] else '0.00'
    
    raw_str = f'{date}|{acct}|{type_}|{symbol}|{amount}'
    return hashlib.md5(raw_str.encode()).hexdigest()

def check_staged_transactions():
    conn = sqlite3.connect('database/portfolio.db')

    # 1. Get Staged Data
    df_staging = pd.read_sql_query('SELECT * FROM transactions_staging ORDER BY TradeDate', conn)

    if df_staging.empty:
        print("No transactions in staging.")
        conn.close()
        return

    # 2. Get Existing Data for Comparison
    # We pull a subset of columns to build hashes for checking
    try:
        df_existing = pd.read_sql_query('SELECT TradeDate, AccountID, Type, Symbol, Amount_Base FROM transactions', conn)
        existing_hashes = set(df_existing.apply(generate_txn_hash, axis=1))
    except Exception as e:
        print(f"Could not read existing transactions: {e}")
        existing_hashes = set()

    print(f'\n{len(df_staging)} Transactions in Staging:\n')
    
    # Header
    print(f"{'Date':<12} | {'Account':<10} | {'Type':<12} | {'Symbol':<20} | {'Amount (NOK)':>15} | {'Status'}")
    print('-' * 95)

    for idx, row in df_staging.iterrows():
        row_hash = generate_txn_hash(row)
        is_dupe = row_hash in existing_hashes
        status = ' [!] POSSIBLE DUPLICATE' if is_dupe else ' OK'
        
        # Format date
        date_str = str(row['TradeDate']).split(' ')[0]
        
        # Truncate symbol
        sym = str(row['Symbol']) if row['Symbol'] else ''
        if len(sym) > 19: sym = sym[:16] + '...'
        
        print(f"{date_str:<12} | {str(row['AccountID']):<10} | {row['Type']:<12} | {sym:<20} | {row['Amount_Base']:>15,.2f} |{status}")

    conn.close()

if __name__ == "__main__":
    check_staged_transactions()
