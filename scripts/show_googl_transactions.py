import sqlite3
import pandas as pd

DB_FILE = 'database/portfolio.db'

def get_transactions_for_symbol(symbol):
    """
    Fetches and displays all transactions for a given stock symbol.
    """
    conn = sqlite3.connect(DB_FILE)
    
    # First, find the ISIN for the given symbol
    c = conn.cursor()
    c.execute("SELECT ISIN FROM isin_symbol_map WHERE Symbol = ?", (symbol,))
    result = c.fetchone()
    
    if result is None:
        print(f"Could not find ISIN for symbol: {symbol}")
        conn.close()
        return
        
    isin = result[0]
    
    # Now, fetch all transactions for that ISIN
    query = f"""
    SELECT 
        TradeDate, 
        Type, 
        Quantity, 
        Price, 
        Amount_Base, 
        Currency_Local, 
        ExchangeRate 
    FROM transactions 
    WHERE ISIN = '{isin}' 
    AND Type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT')
    ORDER BY TradeDate
    """
    
    df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    if df.empty:
        print(f"No transactions found for {symbol} (ISIN: {isin})")
    else:
        print(f"--- Transactions for {symbol} (ISIN: {isin}) ---")
        print(df.to_string())

if __name__ == '__main__':
    get_transactions_for_symbol('GOOGL')
