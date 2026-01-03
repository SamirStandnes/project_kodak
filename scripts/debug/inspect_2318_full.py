from scripts.shared.db import execute_query
import pandas as pd
from rich.console import Console
from rich.table import Table

def query_2318_all():
    query = """
        SELECT t.*, i.symbol as inst_symbol
        FROM transactions t
        JOIN instruments i ON t.instrument_id = i.id
        WHERE i.symbol = '2318.HK'
        ORDER BY t.date
    """
    results = execute_query(query)
    df = pd.DataFrame([dict(r) for r in results])
    
    # Use pandas to display all columns clearly
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df)

if __name__ == "__main__":
    query_2318_all()
