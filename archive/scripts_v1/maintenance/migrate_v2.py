import sqlite3
import pandas as pd
import os

OLD_DB = 'database/portfolio.db'
NEW_DB = 'database/portfolio_v2.db'

def migrate():
    if not os.path.exists(OLD_DB):
        print(f"Old database not found at {OLD_DB}")
        return
    if not os.path.exists(NEW_DB):
        print(f"New database not found at {NEW_DB}. Run create_v2_schema.py first.")
        return

    conn_old = sqlite3.connect(OLD_DB)
    conn_new = sqlite3.connect(NEW_DB)
    c_new = conn_new.cursor()

    print("--- 1. Migrating Accounts ---")
    # Get unique accounts from old transactions
    # Deduplicate by AccountID, taking the first Source encountered
    df_accounts_raw = pd.read_sql_query("SELECT DISTINCT AccountID, Source FROM transactions", conn_old)
    df_accounts = df_accounts_raw.groupby('AccountID').first().reset_index()
    
    account_map = {} # external_id -> new_id
    
    for _, row in df_accounts.iterrows():
        ext_id = str(row['AccountID'])
        broker = row['Source']
        
        # Determine likely name and currency (defaulting to NOK for now as per user context)
        name = f"{broker} {ext_id}"
        currency = 'NOK' 
        
        c_new.execute('''
            INSERT INTO accounts (name, broker, currency, external_id)
            VALUES (?, ?, ?, ?)
        ''', (name, broker, currency, ext_id))
        
        account_map[ext_id] = c_new.lastrowid
    
    print(f"Migrated {len(account_map)} accounts.")

    print("--- 2. Migrating Instruments ---")
    # Get unique instruments. Prefer ISIN as key.
    # Group by ISIN and take the most common Symbol if multiple exist, or just the first.
    df_instruments = pd.read_sql_query('''
        SELECT ISIN, Symbol, MAX(TradeDate) as LastTrade 
        FROM transactions 
        WHERE ISIN IS NOT NULL AND ISIN != '' 
        GROUP BY ISIN
    ''', conn_old)

    isin_map = {} # ISIN -> new_id
    
    for _, row in df_instruments.iterrows():
        isin = row['ISIN']
        symbol = row['Symbol']
        
        c_new.execute('''
            INSERT INTO instruments (isin, symbol)
            VALUES (?, ?)
        ''', (isin, symbol))
        
        isin_map[isin] = c_new.lastrowid
        
    print(f"Migrated {len(isin_map)} instruments.")

    print("--- 3. Migrating Transactions ---")
    df_trans = pd.read_sql_query("SELECT * FROM transactions", conn_old)
    
    count = 0
    for _, row in df_trans.iterrows():
        ext_acc_id = str(row['AccountID'])
        acc_id = account_map.get(ext_acc_id)
        
        isin = row['ISIN']
        inst_id = isin_map.get(isin) if isin else None
        
        # Fix date format if necessary (assuming YYYY-MM-DD or similar in old db)
        
        c_new.execute('''
            INSERT INTO transactions (
                external_id, account_id, instrument_id,
                date, type, quantity, price,
                amount, currency, exchange_rate, amount_local
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['GlobalID'],
            acc_id,
            inst_id,
            row['TradeDate'],
            row['Type'],
            row['Quantity'],
            row['Price'],
            row['Amount_Raw'],
            row['Currency_Raw'],
            row['ExchangeRate'],
            row['Amount_NOK']
        ))
        count += 1
        
    conn_new.commit()
    print(f"Migrated {count} transactions.")
    
    conn_old.close()
    conn_new.close()

if __name__ == '__main__':
    migrate()