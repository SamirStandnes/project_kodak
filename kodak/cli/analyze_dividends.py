from kodak.shared.db import get_connection
from kodak.shared.calculations import get_dividend_details
from kodak.shared.utils import load_config
from rich.console import Console
from rich.table import Table

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run_dividend_report():
    console = Console()
    df_yearly, df_2025, df_all = get_dividend_details()

    # 1. Yearly Table
    table_yearly = Table(title=f"Dividends by Year ({BASE_CURRENCY})")
    table_yearly.add_column("Year", style="cyan")
    table_yearly.add_column(f"Total Dividends ({BASE_CURRENCY})", justify="right", style="green")

    for _, row in df_yearly.iterrows():
        table_yearly.add_row(row['year'], f"{row['total']:,.0f}")

    console.print(table_yearly)

    # 2. 2025 Table
    table_2025 = Table(title=f"Top Dividend Payers (2025) - {BASE_CURRENCY}")
    table_2025.add_column("Instrument", style="magenta")
    table_2025.add_column(f"Total ({BASE_CURRENCY})", justify="right", style="green")

    for _, row in df_2025.head(10).iterrows():
        table_2025.add_row(row['symbol'], f"{row['total']:,.0f}")

    console.print(table_2025)

    # 3. All Time Table
    table_all = Table(title=f"Top Dividend Payers (All Time) - {BASE_CURRENCY}")
    table_all.add_column("Instrument", style="magenta")
    table_all.add_column(f"Total ({BASE_CURRENCY})", justify="right", style="green")

    for _, row in df_all.head(15).iterrows():
        table_all.add_row(row['symbol'], f"{row['total']:,.0f}")

    console.print(table_all)

if __name__ == "__main__":
    run_dividend_report()