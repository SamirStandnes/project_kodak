import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.db import get_connection

def analyze_interest():
    console = Console()
    conn = get_connection()
    
    console.print("\n[bold cyan]--- Interest Expense Analysis ---[/bold cyan]\n")

    # 1. Total Interest by Year
    query_yearly = """
        SELECT 
            strftime('%Y', date) as year, 
            SUM(amount_local) as total_interest_nok
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY year
        ORDER BY year DESC
    """
    df_yearly = pd.read_sql_query(query_yearly, conn)
    
    table_yearly = Table(title="Interest by Year", show_header=True, header_style="bold magenta")
    table_yearly.add_column("Year", justify="center")
    table_yearly.add_column("Total Interest (NOK)", justify="right")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(
            row['year'],
            f"{row['total_interest_nok']:,.2f}"
        )
    console.print(table_yearly)
    console.print()

    # 2. Total Interest by Currency
    query_currency = """
        SELECT 
            currency, 
            SUM(amount) as total_interest_currency,
            SUM(amount_local) as total_interest_nok
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY currency
        ORDER BY total_interest_nok ASC
    """
    df_currency = pd.read_sql_query(query_currency, conn)
    
    table_curr = Table(title="Interest by Currency", show_header=True, header_style="bold magenta")
    table_curr.add_column("Currency", justify="center")
    table_curr.add_column("Total (Native)", justify="right")
    table_curr.add_column("Total (NOK)", justify="right")
    
    for _, row in df_currency.iterrows():
        table_curr.add_row(
            row['currency'],
            f"{row['total_interest_currency']:,.2f}",
            f"{row['total_interest_nok']:,.2f}"
        )
    console.print(table_curr)
    console.print()

    # 3. Top 10 Largest Interest Payments
    query_top = """
        SELECT 
            date, 
            currency, 
            amount, 
            amount_local,
            notes
        FROM transactions
        WHERE type = 'INTEREST'
        ORDER BY amount_local ASC
        LIMIT 10
    """
    df_top = pd.read_sql_query(query_top, conn)
    
    table_top = Table(title="Top 10 Largest Interest Payments", show_header=True, header_style="bold magenta")
    table_top.add_column("Date", justify="center")
    table_top.add_column("Notes")
    table_top.add_column("Amount", justify="right")
    table_top.add_column("Amount (NOK)", justify="right")
    
    for _, row in df_top.iterrows():
        table_top.add_row(
            row['date'],
            row['notes'] or "",
            f"{row['amount']:,.2f} {row['currency']}",
            f"{row['amount_local']:,.2f}"
        )
    console.print(table_top)
    
    conn.close()

if __name__ == "__main__":
    analyze_interest()
