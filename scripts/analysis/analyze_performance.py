import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.calculations import get_realized_performance

def analyze_performance():
    console = Console()
    console.print("\n[bold cyan]--- Yearly Performance Analysis (Realized) ---[/bold cyan]\n")
    
    df = get_realized_performance()
    
    if df.empty:
        console.print("[yellow]No data available.[/yellow]")
        return

    # Create Table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Year", justify="center")
    table.add_column("Realized GL", justify="right")
    table.add_column("Dividends", justify="right")
    table.add_column("Interest", justify="right")
    table.add_column("Fees", justify="right")
    table.add_column("Tax", justify="right")
    table.add_column("Total P&L", justify="right", style="bold")

    # Add Rows
    for _, row in df.iterrows():
        total_style = "green" if row['total_pl'] >= 0 else "red"
        
        table.add_row(
            row['year'],
            f"{row['realized_gl']:,.0f}",
            f"{row['dividends']:,.0f}",
            f"{row['interest']:,.0f}",
            f"{row['fees']:,.0f}",
            f"{row['tax']:,.0f}",
            f"[{total_style}]{row['total_pl']:,.0f}[/{total_style}]"
        )
        
    console.print(table)
    
    # Grand Total
    total_pl = df['total_pl'].sum()
    console.print(f"\n[bold]Grand Total Realized P&L (All Time):[/bold] {total_pl:,.0f} NOK")

if __name__ == '__main__':
    analyze_performance()
