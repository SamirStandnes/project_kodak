import sqlite3
import pandas as pd

def show_all_transactions_for_security(account_id, symbol):
    """
    Shows all transactions for a specific security within a specific account.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    
    # Get the ISIN for the given symbol
    c = conn.cursor()
    c.execute('SELECT ISIN FROM isin_symbol_map WHERE Symbol = ?', (symbol,))
    isin_result = c.fetchone()
    
    if not isin_result:
        print(f"Could not find ISIN for symbol {symbol}")
        conn.close()
        return
        
    isin = isin_result[0]
    
    query = f'''
        SELECT
            *
        FROM
            transactions
        WHERE
            AccountID = '{account_id}'
            AND ISIN = '{isin}'
        ORDER BY
            TradeDate
    '''
    
    try:
        df = pd.read_sql_query(query, conn)
        
        print(f'--- All Transactions for {symbol} ({isin}) in Account: {account_id} ---')
        
        if df.empty:
            print("No transactions found for this security in this account.")
        else:
            print(df.to_string())

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python show_all_transactions_for_security.py <ISIN_OR_SYMBOL> [ACCOUNT_ID]")
        sys.exit(1)

    security_identifier = sys.argv[1]
    account_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Determine if input is ISIN or Symbol
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Try to find if it is a known Symbol first
    c.execute('SELECT ISIN FROM isin_symbol_map WHERE Symbol = ?', (security_identifier,))
    res = c.fetchone()
    
    if res:
        isin = res[0]
        symbol = security_identifier
    else:
        # Assume it is an ISIN
        isin = security_identifier
        # Try to find symbol
        c.execute('SELECT Symbol FROM isin_symbol_map WHERE ISIN = ?', (isin,))
        res_sym = c.fetchone()
        symbol = res_sym[0] if res_sym else "Unknown"

    conn.close()

    if account_id:
        show_all_transactions_for_security(account_id, symbol)
    else:
        # If no account specified, find all accounts with this ISIN
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT DISTINCT AccountID FROM transactions WHERE ISIN = ?", (isin,))
        accounts = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not accounts:
            print(f"No transactions found for {security_identifier}")
        
        for acc in accounts:
            show_all_transactions_for_security(acc, symbol)
