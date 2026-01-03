import sys
import argparse
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from scripts.shared.calculations import get_yearly_equity_curve, get_yearly_contribution, get_total_xirr
from scripts.shared.utils import load_config

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run_report():
    parser = argparse.ArgumentParser(description="Kodak Portfolio Performance Report")
    parser.add_argument("year", nargs="?", help="Year to analyze in detail (e.g., 2021)")
    parser.add_argument("--total", action="store_true", help="Show only All-Time XIRR")
    parser.add_argument("--timeline", action="store_true", help="Show only Yearly Timeline")
    
    args = parser.parse_args()
    console = Console()
    
    # Header
    console.print("\n[bold white on blue]  KODAK PORTFOLIO PERFORMANCE REPORT  [/bold white on blue]\n")
    
    # 1. ALL-TIME XIRR (Default or --total)
    if args.total or (not args.timeline and not args.year):
        console.print(Panel("[bold green]Calculating All-Time Performance...[/bold green]", expand=False))
        total_xirr = get_total_xirr()
        console.print(f"  [bold cyan]ALL-TIME XIRR:[/bold cyan] [bold green]{total_xirr:.2f}%[/bold green] (Annualized)\n")
        
        if args.total: return

    # 2. YEARLY TIMELINE (Default, --timeline, or implied by --year if we want context?)
    
    df_years = pd.DataFrame() 
    
    if args.timeline or (not args.total and not args.year):
        console.print("[bold yellow]Yearly Summary Timeline[/bold yellow]")
        df_years, missing_prices_timeline = get_yearly_equity_curve()
        
        if df_years.empty:
            console.print("[red]No data found.[/red]")
            return

        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Year", justify="center")
        summary_table.add_column("Start Value", justify="right")
        summary_table.add_column("Net Deposits", justify="right", style="cyan")
        summary_table.add_column("End Value", justify="right")
        summary_table.add_column(f"Profit ({BASE_CURRENCY})", justify="right")
        summary_table.add_column("XIRR %", justify="right", style="bold yellow")

        for _, row in df_years.iterrows():
            p_style = "green" if row['profit'] >= 0 else "red"
            r_style = "green" if row['return_pct'] >= 0 else "red"
            
            summary_table.add_row(
                row['year'],
                f"{row['start_equity']:,.0f}",
                f"{row['net_flow']:,.0f}",
                f"{row['end_equity']:,.0f}",
                f"[{p_style}]{row['profit']:,.0f}[/{p_style}]",
                f"[{r_style}]{row['return_pct']:.2f}%[/{r_style}]"
            )
        console.print(summary_table)
        
        if missing_prices_timeline:
            console.print("\n[bold red]WARNING: Missing or Fallback Prices Used in Timeline[/bold red]")
            warn_table = Table(show_header=True, header_style="bold red")
            warn_table.add_column("Symbol", style="bold")
            warn_table.add_column("Date")
            warn_table.add_column("Type", style="yellow")
            warn_table.add_column("Price Used", justify="right")
            
            for m in missing_prices_timeline:
                warn_table.add_row(m['symbol'], str(m['date']), m['type'], f"{m['price']:.4f}")
            console.print(warn_table)
        
        console.print()

    # 3. SPECIFIC YEAR DETAIL
    if args.year:
        target_year = str(args.year)
        
        # We need df_years to show the summary row for that year.
        # If we skipped step 2, we need to fetch it or just fetch single line logic?
        # get_yearly_equity_curve returns all years. It's fine to call it if needed.
        if df_years.empty:
             # If user ran with --total AND year (weird combo) or just `report 2021` (default skips timeline?)
             # Wait, logic above: if args.year is set, we skipped step 2.
             # So we need to fetch curve to get the summary row for the table footer.
             df_years, _ = get_yearly_equity_curve()

        if target_year not in df_years['year'].values:
            console.print(f"\n[red]No detailed data found for year {target_year}.[/red]")
        else:
            console.print(f"\n[bold white on cyan] --- YEAR {target_year} DETAILS --- [/bold white on cyan]")
            df_contrib, year_total_xirr, missing_prices = get_yearly_contribution(target_year)
            
            detail_table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
            detail_table.add_column("Instrument", style="bold", width=40)
            detail_table.add_column("SOY Value", justify="right", width=12)
            detail_table.add_column("Net Additions", justify="right", width=12, style="cyan")
            detail_table.add_column("EOY Value", justify="right", width=12)
            detail_table.add_column("Divs", justify="right", width=10, style="green")
            detail_table.add_column("Profit", justify="right", width=12)
            detail_table.add_column("IRR %", justify="right", width=10, style="bold yellow")
            detail_table.add_column("Contr. %", justify="right", width=10, style="bold cyan")

            for _, row in df_contrib.iterrows():
                p_style = "green" if row['Profit'] >= 0 else "red"
                c_style = "green" if row['Contribution %'] >= 0 else "red"
                i_style = "green" if row['IRR %'] >= 0 else "red"
                row_style = "dim" if "*" in row['Symbol'] or "[" in row['Symbol'] else ""
                
                detail_table.add_row(
                    row['Symbol'], f"{row['SOY Value']:,.0f}", f"{row['Net Additions']:,.0f}",
                    f"{row['EOY Value']:,.0f}", f"{row['Dividends']:,.0f}",
                    f"[{p_style}]{row['Profit']:,.0f}[/{p_style}]",
                    f"[{i_style}]{row['IRR %']:.1f}%[/{i_style}]",
                    f"[{c_style}]{row['Contribution %']:.2f}%[/{c_style}]",
                    style=row_style
                )
            
            detail_table.add_section()
            sum_row = df_years[df_years['year'] == target_year].iloc[0]
            detail_table.add_row(
                f"TOTAL {target_year}", f"{sum_row['start_equity']:,.0f}", f"{sum_row['net_flow']:,.0f}",
                f"{sum_row['end_equity']:,.0f}", f"{df_contrib['Dividends'].sum():,.0f}",
                f"{sum_row['profit']:,.0f}", f"{year_total_xirr:.2f}%", f"{year_total_xirr:.2f}%",
                style="bold white on blue"
            )
            console.print(detail_table)

            if missing_prices:
                console.print("\n[bold red]WARNING: Missing or Fallback Prices Used[/bold red]")
                warn_table = Table(show_header=True, header_style="bold red")
                warn_table.add_column("Symbol", style="bold")
                warn_table.add_column("Date")
                warn_table.add_column("Type", style="yellow")
                warn_table.add_column("Price Used", justify="right")
                
                for m in missing_prices:
                    warn_table.add_row(m['symbol'], str(m['date']), m['type'], f"{m['price']:.4f}")
                
                console.print(warn_table)

    if not args.year and not args.total and not args.timeline:
        console.print(f"\n[dim]Tip: Run with '2021', '--total', or '--timeline' for specific views.[/dim]")

    console.print("\n[bold green]Report Complete.[/bold green]")

if __name__ == '__main__':
    run_report()
