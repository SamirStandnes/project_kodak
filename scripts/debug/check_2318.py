from scripts.shared.db import execute_query
import pandas as pd
from rich.console import Console
from rich.table import Table

def check_2318():
    query = """
        SELECT t.date, t.type, t.quantity, t.amount_local, t.price, t.currency, t.exchange_rate, i.symbol
        FROM transactions t
        JOIN instruments i ON t.instrument_id = i.id
        WHERE i.symbol = '2318.HK'
        ORDER BY t.date
    """
    results = execute_query(query)
    df = pd.DataFrame([dict(r) for r in results])
    
    console = Console()
    table = Table(title="History for 2318.HK")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Amt (NOK)", justify="right")
    table.add_column("FX Rate", justify="right")
    
    for _, row in df.iterrows():
        table.add_row(
            row['date'], 
            row['type'], 
            f"{row['quantity']:.0f}", 
            f"{row['price']:.2f}",
            f"{row['amount_local']:,.0f}",
            f"{row['exchange_rate']:.4f}"
        )
        
    console.print(table)

if __name__ == "__main__":
    check_2318()
