import pandas as pd
from scripts.shared.db import get_connection, execute_non_query, execute_scalar, execute_query, create_backup

def review_and_commit():
    conn = get_connection()
    
    # Check Staging
    try:
        df = pd.read_sql("SELECT * FROM transactions_staging", conn)
    except:
        print("Staging table does not exist or is empty.")
        conn.close()
        return

    if df.empty:
        print("No transactions in staging.")
        conn.close()
        return

    print(f"\n--- REVIEW STAGING ({len(df)} transactions) ---")
    print(df[['date', 'type', 'symbol', 'amount', 'currency']].head(10).to_string())
    if len(df) > 10:
        print(f"... and {len(df)-10} more.")

    # Check for New Accounts/Instruments
    staged_accs = df['account_external_id'].unique()
    staged_isins = df['isin'].unique()
    
    # Find unknown accounts
    unknown_accs = []
    for acc in staged_accs:
        exists = execute_scalar("SELECT 1 FROM accounts WHERE external_id = ?", (acc,))
        if not exists:
            unknown_accs.append(acc)
            
    # Find unknown instruments
    unknown_insts = []
    for isin in staged_isins:
        if not isin: continue
        exists = execute_scalar("SELECT 1 FROM instruments WHERE isin = ?", (isin,))
        if not exists:
            unknown_insts.append(isin)

    if unknown_accs:
        print(f"\n[!] WARNING: {len(unknown_accs)} New Accounts detected:")
        print(unknown_accs)
        print("They will be auto-created with default settings.")

    if unknown_insts:
        print(f"\n[!] NOTICE: {len(unknown_insts)} New Instruments detected.")

    choice = input("\nCommit these transactions? (y/n/clear): ").lower().strip()
    
    if choice == 'clear':
        execute_non_query("DELETE FROM transactions_staging")
        print("Staging cleared.")
    elif choice == 'y':
        create_backup("before_commit")
        _commit_data(df, unknown_accs, unknown_insts)
    else:
        print("Operation cancelled.")
    
    conn.close()

def _commit_data(df, new_accs, new_isins):
    print("Committing...")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Create New Accounts
        for acc_ext in new_accs:
            # Try to infer broker from ID or source file (simplified here)
            name = f"New Account {acc_ext}"
            cursor.execute("INSERT INTO accounts (name, external_id, currency) VALUES (?, ?, 'NOK')", (name, acc_ext))
            print(f"Created account: {name}")

        # 2. Create New Instruments
        # We need symbol from the dataframe for these ISINs
        unique_instruments = df[df['isin'].isin(new_isins)][['isin', 'symbol']].drop_duplicates('isin')
        for _, row in unique_instruments.iterrows():
            cursor.execute("INSERT INTO instruments (isin, symbol) VALUES (?, ?)", (row['isin'], row['symbol']))
            # print(f"Created instrument: {row['symbol']} ({row['isin']})")

        # 3. Insert Transactions
        # Prepare cache for lookups using the SAME cursor/connection to see uncommitted changes
        cursor.execute("SELECT external_id, id FROM accounts")
        acc_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT isin, id FROM instruments")
        inst_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        count = 0
        for _, row in df.iterrows():
            acc_id = acc_map.get(row['account_external_id'])
            inst_id = inst_map.get(row['isin'])
            
            # Skip if account missing (should not happen if logic above is correct)
            if acc_id is None:
                print(f"Error: Account {row['account_external_id']} not found in map.")
                continue
            
            cursor.execute('''
                INSERT INTO transactions (
                    external_id, account_id, instrument_id, date, type,
                    quantity, price, amount, currency,
                    amount_local, exchange_rate, fee, fee_currency, fee_local, notes, batch_id, source_file, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['external_id'], acc_id, inst_id, row['date'], row['type'],
                row['quantity'], row['price'], row['amount'], row['currency'],
                row['amount_local'], row['exchange_rate'], row['fee'], row.get('fee_currency'), row.get('fee_local'), row['description'], row.get('batch_id'), row.get('source_file'), row.get('hash')
            ))
            count += 1
            
        # 4. Clear Staging
        cursor.execute("DELETE FROM transactions_staging")
        
        conn.commit()
        print(f"Successfully committed {count} transactions.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during commit: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    review_and_commit()
