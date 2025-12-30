import sqlite3
import yfinance as yf
from datetime import datetime

def get_current_holdings(db_file):
    """
    Calculates current holdings from the transactions table.
    Returns a list of ISINs for securities with a quantity greater than zero.
    """
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''
        SELECT ISIN, SUM(Quantity) as TotalQuantity
        FROM transactions
        WHERE ISIN IS NOT NULL
        GROUP BY ISIN
        HAVING TotalQuantity > 0
    ''')
    holdings = [row[0] for row in c.fetchall()]
    conn.close()
    return holdings

def get_symbol_from_map(db_file, isin):
    """
    Gets the ticker symbol for a given ISIN from the isin_symbol_map table.
    """
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT Symbol FROM isin_symbol_map WHERE ISIN = ?', (isin,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_price_from_symbol(symbol):
    """
    Gets the latest price for a given symbol using the yfinance library.
    """
    try:
        ticker = yf.Ticker(symbol)
        # Use 5d to handle weekends/holidays
        hist = ticker.history(period="5d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        else:
            print(f"No history found for symbol {symbol}")
            return None
    except Exception as e:
        print(f"An unexpected error occurred for {symbol}: {e}")
        return None

def fetch_and_store_prices():
    """
    Fetches current prices for unique ISINs from the database.
    It prioritizes the manually mapped symbol, and falls back to the ISIN if no mapping exists.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Create current_prices table if it doesn't exist
    c.execute('DROP TABLE IF EXISTS current_prices')
    c.execute('''
        CREATE TABLE IF NOT EXISTS current_prices (
            ISIN TEXT PRIMARY KEY,
            Price REAL,
            Timestamp TEXT
        )
    ''')
    conn.commit()

    # Get ISINs for currently held securities
    isins = get_current_holdings(db_file)

    print(f"Fetching prices for {len(isins)} currently held securities...")

    for isin in isins:
        price = None
        identifier = None
        
        # Prioritize the mapped symbol
        symbol = get_symbol_from_map(db_file, isin)
        
        if symbol:
            print(f"Attempting to fetch price for {isin} using mapped symbol: {symbol}")
            price = get_price_from_symbol(symbol)
            identifier = symbol
        else:
            # If no mapped symbol, fall back to ISIN
            print(f"No mapped symbol for {isin}. Attempting to use ISIN directly.")
            price = get_price_from_symbol(isin)
            identifier = isin

        if price is not None:
            timestamp = datetime.now().isoformat()
            c.execute('''
                REPLACE INTO current_prices (ISIN, Price, Timestamp)
                VALUES (?, ?, ?)
            ''', (isin, price, timestamp))
            print(f"Fetched price for {isin} (using {identifier}): {price}")
        else:
            print(f"Could not retrieve price for {isin} using either mapped symbol or ISIN.")

    conn.commit()
    conn.close()
    print("Price fetching process completed.")

if __name__ == '__main__':
    fetch_and_store_prices()
