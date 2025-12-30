from scripts.shared.db import execute_query
from scripts.shared.market_data import get_latest_prices, store_prices

def update_prices():
    # 1. Identify what we hold
    # (Simplified: Just get everything we ever bought for now, or use a holdings view)
    rows = execute_query('''
        SELECT DISTINCT instrument_id 
        FROM transactions 
        WHERE instrument_id IS NOT NULL
    ''')
    
    inst_ids = [row['instrument_id'] for row in rows]
    
    if not inst_ids:
        print("No instruments found in database.")
        return

    # 2. Fetch
    prices = get_latest_prices(inst_ids)
    
    # 3. Store
    store_prices(prices)

if __name__ == '__main__':
    update_prices()
