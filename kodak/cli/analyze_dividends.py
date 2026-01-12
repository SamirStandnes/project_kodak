from kodak.shared.db import get_connection
from kodak.shared.calculations import get_dividend_details, get_dividend_forecast
from kodak.shared.utils import load_config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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


def run_dividend_forecast():
    """Display estimated annual dividend income."""
    console = Console()

    console.print("\n[bold]Fetching dividend forecast data...[/bold]\n")
    df, summary = get_dividend_forecast()

    if df.empty:
        console.print("[yellow]No dividend-paying holdings found.[/yellow]")
        return

    # Summary Panel
    summary_text = (
        f"[bold green]Estimated Annual Dividends: {summary['total_estimate_local']:,.0f} {BASE_CURRENCY}[/bold green]\n\n"
        f"Data sources:\n"
        f"  Yahoo Finance (forward): {summary['yahoo_count']} holdings\n"
        f"  TTM History (fallback):  {summary['ttm_count']} holdings\n"
        f"  No dividend data:        {summary['no_data_count']} holdings"
    )
    console.print(Panel(summary_text, title="Dividend Forecast Summary", border_style="green"))

    # Details Table
    table = Table(title=f"Estimated Annual Dividends by Holding")
    table.add_column("Symbol", style="cyan")
    table.add_column("Qty", justify="right")
    table.add_column("Div/Share", justify="right")
    table.add_column("Currency", justify="center")
    table.add_column("Annual Est.", justify="right")
    table.add_column(f"Est. ({BASE_CURRENCY})", justify="right", style="green")
    table.add_column("Source", justify="center", style="dim")

    for _, row in df.iterrows():
        source_style = "green" if row['source'] == 'yahoo' else "yellow"
        table.add_row(
            row['symbol'],
            f"{row['quantity']:,.0f}",
            f"{row['dividend_per_share']:.2f}",
            row['currency'],
            f"{row['annual_estimate']:,.0f}",
            f"{row['annual_estimate_local']:,.0f}",
            f"[{source_style}]{row['source']}[/{source_style}]"
        )

    console.print(table)

    # Legend
    console.print("\n[dim]Source legend: [green]yahoo[/green] = Forward dividend rate | [yellow]ttm[/yellow] = Trailing 12-month history[/dim]")


if __name__ == "__main__":
    run_dividend_report()
    print()
    run_dividend_forecast()