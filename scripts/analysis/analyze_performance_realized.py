from scripts.shared.db import get_connection
from scripts.shared.calculations import get_realized_performance
from scripts.shared.utils import load_config
from rich.console import Console
from rich.table import Table

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run():
    console = Console()
    console.print("\n[bold cyan]--- Yearly Performance Analysis (Realized) ---[/bold cyan]\n")
    
    df = get_realized_performance()

    if df.empty:
        console.print("[yellow]No data available.[/yellow]")
        return

    # Create Table
    table = Table(title=f"Realized Performance (Annual) - {BASE_CURRENCY}")
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
        
        # Helper to format and style individual cells if needed, 
        # but here we just format numbers.
        
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
    total_style = "green" if total_pl >= 0 else "red"
    console.print(f"\n[bold]Grand Total Realized P&L (All Time):[/bold] [{total_style}]{total_pl:,.0f} {BASE_CURRENCY}[/{total_style}]")

if __name__ == '__main__':
    analyze_performance()
