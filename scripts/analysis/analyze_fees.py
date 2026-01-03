from scripts.shared.db import get_connection
from scripts.shared.calculations import get_fee_details
from scripts.shared.utils import load_config
from rich.console import Console
from rich.table import Table

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run_fee_report():
    console = Console()
    console.print("\n[bold cyan]--- Fee Analysis ---[/bold cyan]\n")

    # Fetch Data
    df_yearly, df_currency, df_top = get_fee_details()
    
    # 1. Yearly
    table_yearly = Table(title=f"Fees by Year ({BASE_CURRENCY})")
    table_yearly.add_column("Year", style="cyan")
    table_yearly.add_column(f"Total Fees ({BASE_CURRENCY})", justify="right", style="red")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(row['year'], f"{row['total']:,.2f}")
    console.print(table_yearly)
    console.print()

    # 2. By Currency
    table_curr = Table(title=f"Fees by Currency ({BASE_CURRENCY})")
    table_curr.add_column("Currency", style="magenta")
    table_curr.add_column(f"Total ({BASE_CURRENCY})", justify="right", style="red")
    
    for _, row in df_currency.iterrows():
        table_curr.add_row(row['currency'], f"{row['total']:,.2f}")
    console.print(table_curr)
    console.print()
    
    # 3. Top Recent
    table_top = Table(title=f"Recent Individual Fees ({BASE_CURRENCY})")
    table_top.add_column("Date", style="cyan")
    table_top.add_column("Currency", style="dim")
    table_top.add_column(f"Amount ({BASE_CURRENCY})", justify="right", style="red")
    
    for _, row in df_top.head(10).iterrows():
        table_top.add_row(
            row['date'],
            row['description'] or "",
            f"{row['amount_local']:,.2f}"
        )
    console.print(table_top)

if __name__ == "__main__":
    analyze_fees()
