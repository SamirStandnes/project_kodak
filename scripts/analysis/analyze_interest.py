import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.calculations import get_interest_details

def analyze_interest():
    console = Console()
    console.print("\n[bold cyan]--- Interest Analysis ---[/bold cyan]\n")

    # Fetch Data
    df_yearly, df_currency, df_top = get_interest_details()
    
    # 1. Yearly
    table_yearly = Table(title="Interest by Year", show_header=True, header_style="bold magenta")
    table_yearly.add_column("Year", justify="center")
    table_yearly.add_column("Total Interest (NOK)", justify="right")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(row['year'], f"{row['total']:,.2f}")
    console.print(table_yearly)
    console.print()

    # 2. By Currency
    table_curr = Table(title="Interest by Currency", show_header=True, header_style="bold magenta")
    table_curr.add_column("Currency", justify="center")
    table_curr.add_column("Total (NOK)", justify="right")
    
    for _, row in df_currency.iterrows():
        table_curr.add_row(row['currency'], f"{row['total']:,.2f}")
    console.print(table_curr)
    console.print()
    
    # 3. Top Payments
    table_top = Table(title="Largest Interest Payments", show_header=True, header_style="bold magenta")
    table_top.add_column("Date", justify="center")
    table_top.add_column("Currency")
    table_top.add_column("Amount", justify="right")
    table_top.add_column("Amount (NOK)", justify="right")
    
    for _, row in df_top.head(10).iterrows():
        table_top.add_row(
            row['date'],
            row['currency'],
            f"{row['amount']:,.2f}",
            f"{row['amount_local']:,.2f}"
        )
    console.print(table_top)

if __name__ == "__main__":
    analyze_interest()
