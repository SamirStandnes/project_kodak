from scripts.shared.db import execute_query
import pandas as pd
from rich.console import Console
from rich.table import Table

def check_2318_details():
    query = """
        SELECT t.amount, t.amount_local, t.currency, t.exchange_rate, t.price
        FROM transactions t
        JOIN instruments i ON t.instrument_id = i.id
        WHERE i.symbol = '2318.HK'
        LIMIT 5
    """
    results = execute_query(query)
    df = pd.DataFrame([dict(r) for r in results])
    print(df)

if __name__ == "__main__":
    check_2318_details()
