from scripts.shared.db import execute_query
import pandas as pd
from rich.console import Console
from rich.table import Table

def check_latest_data():
    query = """
        SELECT 
            a.broker as Broker, 
            a.name as Account, 
            MAX(t.date) as [Latest Transaction],
            COUNT(t.id) as [Total Txns]
        FROM accounts a
        LEFT JOIN transactions t ON a.id = t.account_id
        GROUP BY a.broker, a.name
        ORDER BY [Latest Transaction] DESC
    """
    results = execute_query(query)
    df = pd.DataFrame([dict(r) for r in results])
    
    console = Console()
    table = Table(title="Latest Data per Account")
    
    for col in df.columns:
        table.add_column(col)
        
    for _, row in df.iterrows():
        table.add_row(str(row[0]), str(row[1]), str(row[2]), str(row[3]))
        
    console.print(table)

if __name__ == "__main__":
    check_latest_data()
