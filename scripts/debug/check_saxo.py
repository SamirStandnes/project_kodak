from scripts.shared.db import execute_query
import pandas as pd

def check_saxo_currency():
    # Find transactions for a known Saxo stock (assuming you hold AMZN there, or we check any Saxo trade)
    query = """
        SELECT t.currency, a.broker
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.broker = 'Saxo' AND t.instrument_id IS NOT NULL
        LIMIT 5
    """
    results = execute_query(query)
    if not results:
        print("No Saxo stock trades found.")
    else:
        print(pd.DataFrame([dict(r) for r in results]))

if __name__ == "__main__":
    check_saxo_currency()
