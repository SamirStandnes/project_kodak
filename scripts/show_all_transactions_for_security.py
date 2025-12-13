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
    # Focusing on D05.SI in account 19269921 as per user's request
    show_all_transactions_for_security('19269921', 'D05.SI')
