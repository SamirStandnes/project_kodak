import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.db import get_connection

def analyze_dividends():
    console = Console()
    conn = get_connection()
    
    console.print("\n[bold cyan]--- Dividend Analysis ---[/bold cyan]\n")

    # 1. Total Dividends by Year
    query_yearly = """
        SELECT 
            strftime('%Y', date) as year, 
            SUM(amount_local) as total_dividends_nok
        FROM transactions
        WHERE type = 'DIVIDEND'
        GROUP BY year
        ORDER BY year DESC
    """
    df_yearly = pd.read_sql_query(query_yearly, conn)
    
    table_yearly = Table(title="Dividends by Year", show_header=True, header_style="bold magenta")
    table_yearly.add_column("Year", justify="center")
    table_yearly.add_column("Total Dividends (NOK)", justify="right")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(
            row['year'],
            f"{row['total_dividends_nok']:,.2f}"
        )
    console.print(table_yearly)
    console.print()

    # 2. Dividends by Ticker (2025) - NEW SECTION
    query_2025 = """
        SELECT 
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total_2025_nok
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND' AND t.date LIKE '2025%'
        GROUP BY symbol
        ORDER BY total_2025_nok DESC
    """
    df_2025 = pd.read_sql_query(query_2025, conn)
    
    table_2025 = Table(title="Top Dividend Payers in 2025", show_header=True, header_style="bold magenta")
    table_2025.add_column("Symbol", style="cyan")
    table_2025.add_column("Total 2025 (NOK)", justify="right")
    
    for _, row in df_2025.iterrows():
        table_2025.add_row(
            row['symbol'] or "Unknown",
            f"{row['total_2025_nok']:,.2f}"
        )
    console.print(table_2025)
    console.print()

    # 3. Top Dividend Paying Stocks (All Time)
    query_stock = """
        SELECT 
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total_dividends_nok
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND'
        GROUP BY symbol
        ORDER BY total_dividends_nok DESC
        LIMIT 10
    """
    df_stock = pd.read_sql_query(query_stock, conn)
    
    table_stock = Table(title="Top 10 Dividend Payers (All Time)", show_header=True, header_style="bold magenta")
    table_stock.add_column("Symbol", style="cyan")
    table_stock.add_column("Total (NOK)", justify="right")
    
    for _, row in df_stock.iterrows():
        table_stock.add_row(
            row['symbol'] or "Unknown",
            f"{row['total_dividends_nok']:,.2f}"
        )
    console.print(table_stock)
    console.print()

    # 4. Top 10 Net Single Payouts (Grouped to handle reversals)
    query_top = """
        SELECT 
            t.date, 
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as net_amount_nok
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND'
        GROUP BY t.date, t.instrument_id
        HAVING net_amount_nok > 0
        ORDER BY net_amount_nok DESC
        LIMIT 10
    """
    df_top = pd.read_sql_query(query_top, conn)
    
    table_top = Table(title="Top 10 Largest Net Payouts (Netted)", show_header=True, header_style="bold magenta")
    table_top.add_column("Date", justify="center")
    table_top.add_column("Symbol", style="cyan")
    table_top.add_column("Net Amount (NOK)", justify="right")
    
    for _, row in df_top.iterrows():
        table_top.add_row(
            row['date'],
            row['symbol'] or "Unknown",
            f"{row['net_amount_nok']:,.2f}"
        )
    console.print(table_top)
    
    conn.close()

if __name__ == "__main__":
    analyze_dividends()