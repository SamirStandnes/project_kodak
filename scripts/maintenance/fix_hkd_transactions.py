from scripts.shared.db import execute_query
import pandas as pd

def dry_run_fix():
    query = """
        SELECT id, amount, amount_local, exchange_rate, currency 
        FROM transactions 
        WHERE instrument_id = 60
    """
    results = execute_query(query)
    df = pd.DataFrame([dict(r) for r in results])
    
    print("--- BEFORE ---")
    print(df.head())
    
    # Simulate Fix
    df['new_currency'] = 'HKD'
    df['new_amount'] = df.apply(lambda row: row['amount_local'] / row['exchange_rate'] if row['exchange_rate'] > 0 else row['amount'], axis=1)
    
    print("\n--- AFTER (SIMULATED) ---")
    print(df[['id', 'amount_local', 'exchange_rate', 'new_amount', 'new_currency']].head())

if __name__ == "__main__":
    dry_run_fix()
