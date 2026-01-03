from scripts.shared.db import get_connection
from scripts.shared.calculations import get_interest_details
from scripts.shared.utils import load_config
from rich.console import Console
from rich.table import Table

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run_interest_report():
    console = Console()
    df_yearly, df_curr, df_top = get_interest_details()

    # 1. Yearly
    table_yearly = Table(title=f"Interest by Year ({BASE_CURRENCY})")
    table_yearly.add_column("Year", style="cyan")
    table_yearly.add_column(f"Total Interest ({BASE_CURRENCY})", justify="right")

    for _, row in df_yearly.iterrows():
        table_yearly.add_row(row['year'], f"{row['total']:,.0f}")

    console.print(table_yearly)

    # 2. By Currency
    table_curr = Table(title=f"Interest by Currency ({BASE_CURRENCY})")
    table_curr.add_column("Currency", style="magenta")
    table_curr.add_column(f"Total ({BASE_CURRENCY})", justify="right")

    for _, row in df_curr.iterrows():
        table_curr.add_row(row['currency'], f"{row['total']:,.0f}")

    console.print(table_curr)

    # 3. Recent Individual
    table_top = Table(title=f"Recent Interest Payments ({BASE_CURRENCY})")
    table_top.add_column("Date", style="cyan")
    table_top.add_column("Currency", style="dim")
    table_top.add_column(f"Amount ({BASE_CURRENCY})", justify="right")
    table_top.add_column("Source", style="dim")

    for _, row in df_top.head(20).iterrows():
        table_top.add_row(row['date'], row['currency'], f"{row['amount_local']:,.0f}", str(row['source_file']))

    console.print(table_top)

if __name__ == "__main__":
    run_interest_report()
