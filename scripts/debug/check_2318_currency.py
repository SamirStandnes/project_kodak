from scripts.shared.db import execute_query
import pandas as pd

def check_2318_currency():
    query = """
        SELECT DISTINCT t.currency 
        FROM transactions t
        JOIN instruments i ON t.instrument_id = i.id
        WHERE i.symbol = '2318.HK'
    """
    results = execute_query(query)
    print(pd.DataFrame([dict(r) for r in results]))

if __name__ == "__main__":
    check_2318_currency()
