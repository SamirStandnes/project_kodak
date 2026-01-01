import sys
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from scripts.shared.calculations import get_yearly_equity_curve, get_yearly_contribution, get_total_xirr

def run_full_report():
    console = Console()
    
    # 1. Handle optional Year argument for drill-down
    target_year = sys.argv[1] if len(sys.argv) > 1 else None

    console.print("\n[bold white on blue]  KODAK PORTFOLIO PERFORMANCE REPORT  [/bold white on blue]\n")
    
    # --- LEVEL 1: ALL-TIME ---
    console.print(Panel("[bold green]Calculating All-Time Performance...[/bold green]", expand=False))
    total_xirr = get_total_xirr()
    console.print(f"  [bold cyan]ALL-TIME XIRR:[/bold cyan] [bold green]{total_xirr:.2f}%[/bold green] (Annualized)\n")

    # --- LEVEL 2: YEARLY SUMMARY ---
    console.print("[bold yellow]Yearly Summary Timeline[/bold yellow]")
    df_years = get_yearly_equity_curve()
    
    if df_years.empty:
        console.print("[red]No data found.[/red]")
        return

    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Year", justify="center")
    summary_table.add_column("Start Value", justify="right")
    summary_table.add_column("Net Deposits", justify="right", style="cyan")
    summary_table.add_column("End Value", justify="right")
    summary_table.add_column("Profit (NOK)", justify="right")
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

    # --- LEVEL 3: OPTIONAL DRILL-DOWN ---
    if target_year:
        if target_year not in df_years['year'].values:
            console.print(f"\n[red]No detailed data found for year {target_year}.[/red]")
        else:
            console.print(f"\n[bold white on cyan] --- YEAR {target_year} DETAILS --- [/bold white on cyan]")
            df_contrib, year_total_xirr = get_yearly_contribution(target_year)
            
            detail_table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
            detail_table.add_column("Instrument", style="bold", width=25)
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
    else:
        console.print(f"\n[dim]Tip: Run 'python -m scripts.analysis.performance_report [YEAR]' for a detailed breakdown.[/dim]")

    console.print("\n[bold green]Report Complete.[/bold green]")

if __name__ == '__main__':
    run_full_report()
