import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.calculations import get_dividend_details

def analyze_dividends():
    console = Console()
    console.print("\n[bold cyan]--- Dividend Analysis ---[/bold cyan]\n")

    # Fetch Data
    df_yearly, df_2025, df_all_time = get_dividend_details()
    
    # 1. Yearly
    table_yearly = Table(title="Dividends by Year", show_header=True, header_style="bold magenta")
    table_yearly.add_column("Year", justify="center")
    table_yearly.add_column("Total Dividends (NOK)", justify="right")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(row['year'], f"{row['total']:,.2f}")
    console.print(table_yearly)
    console.print()

    # 2. Top Payers (2025)
    table_2025 = Table(title="Top Payers (2025)", show_header=True, header_style="bold magenta")
    table_2025.add_column("Symbol", justify="center")
    table_2025.add_column("Total (NOK)", justify="right")
    
    for _, row in df_2025.head(10).iterrows():
        table_2025.add_row(row['symbol'], f"{row['total']:,.2f}")
    console.print(table_2025)
    console.print()
    
    # 3. Top Payers (All Time)
    table_all = Table(title="Top Payers (All Time)", show_header=True, header_style="bold magenta")
    table_all.add_column("Symbol", justify="center")
    table_all.add_column("Total (NOK)", justify="right")
    
    for _, row in df_all_time.head(10).iterrows():
        table_all.add_row(row['symbol'], f"{row['total']:,.2f}")
    console.print(table_all)

if __name__ == "__main__":
    analyze_dividends()