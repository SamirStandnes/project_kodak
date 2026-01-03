import pandas as pd
from kodak.shared.db import get_connection
from kodak.shared.calculations import get_holdings

def check_gaps():
    conn = get_connection()
    holdings = get_holdings()
    
    # 1. Check for holdings without any price in market_prices
    query_prices = "SELECT DISTINCT instrument_id FROM market_prices"
    priced_ids = pd.read_sql_query(query_prices, conn)['instrument_id'].tolist()
    
    unpriced = holdings[~holdings['instrument_id'].isin(priced_ids)]
    
    print("--- Holdings Missing Market Prices ---")
    if not unpriced.empty:
        print(unpriced[['symbol', 'isin', 'quantity', 'account_id']])
    else:
        print("None. All holdings have at least one price entry.")
    
    # 2. Check for instruments missing symbols (often meaning ISIN map failed)
    print("\n--- Instruments Missing Symbols (Ticker) ---")
    query_missing_sym = "SELECT id, isin, name, currency FROM instruments WHERE symbol IS NULL OR symbol = ''"
    missing_sym = pd.read_sql_query(query_missing_sym, conn)
    
    if not missing_sym.empty:
        print(missing_sym)
    else:
        print("None. All instruments have a symbol mapping.")

    # 3. Check for instruments with NO transactions (cleanup candidate)
    print("\n--- Instruments with Zero Transactions ---")
    query_unused = """
        SELECT i.id, i.isin, i.name 
        FROM instruments i
        LEFT JOIN transactions t ON i.id = t.instrument_id
        WHERE t.id IS NULL
    """
    unused = pd.read_sql_query(query_unused, conn)
    if not unused.empty:
        print(unused)
    else:
        print("None.")

    # 4. Check for Stale Prices (Older than 3 days)
    print("\n--- Stale Prices (> 3 days old) for Current Holdings ---")
    query_latest_price = """
        SELECT i.symbol, i.isin, MAX(mp.date) as last_price_date
        FROM market_prices mp
        JOIN instruments i ON mp.instrument_id = i.id
        GROUP BY mp.instrument_id
    """
    latest_prices = pd.read_sql_query(query_latest_price, conn)
    
    # Filter for holdings
    current_holding_ids = holdings['instrument_id'].unique()
    
    stale_mask = pd.to_datetime(latest_prices['last_price_date']) < (pd.Timestamp.now() - pd.Timedelta(days=3))
    stale_prices = latest_prices[stale_mask & latest_prices['symbol'].isin(holdings['symbol'])]
    
    if not stale_prices.empty:
        print(stale_prices)
    else:
        print("None. All holding prices are recent.")

    conn.close()

if __name__ == "__main__":
    check_gaps()
