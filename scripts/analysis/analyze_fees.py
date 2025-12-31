import pandas as pd
from rich.console import Console
from rich.table import Table
from scripts.shared.db import get_connection

def analyze_fees():
    console = Console()
    conn = get_connection()
    
    console.print("\n[bold cyan]--- Fee Analysis ---[/bold cyan]\n")

    # 1. Total Fees by Year
    # Logic: Sum of 'fee_local' column (embedded) + ABS(amount_local) for type='FEE'
    # Actually, if we populated fee_local correctly even for type='FEE' rows (via parser or enrichment), we could just sum fee_local?
    # Wait, for type='FEE' rows, the 'amount' IS the fee. The 'fee' column might be 0.
    # Let's check parsers.py:
    # For Nordnet type='FEE': amount is set. fee is set to clean_num(row['Kurtasje_Clean']). 
    # Usually for type='FEE' transaction, Kurtasje is 0, and the amount is the fee.
    # So we still need the dual logic: 
    #   If type='FEE', use ABS(amount_local). 
    #   If type!='FEE', use fee_local.
    
    query_yearly = """
        SELECT 
            strftime('%Y', date) as year, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total_fees_nok
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY year
        ORDER BY year DESC
    """
    df_yearly = pd.read_sql_query(query_yearly, conn)
    
    table_yearly = Table(title="Fees by Year", show_header=True, header_style="bold magenta")
    table_yearly.add_column("Year", justify="center")
    table_yearly.add_column("Total Fees (NOK)", justify="right")
    
    for _, row in df_yearly.iterrows():
        table_yearly.add_row(
            row['year'],
            f"{row['total_fees_nok']:,.2f}"
        )
    console.print(table_yearly)
    console.print()

    # 2. Total Fees by Currency
    # Group by transaction currency as proxy
    query_currency = """
        SELECT 
            currency, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total_fees_nok
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY currency
        ORDER BY total_fees_nok ASC
    """
    df_currency = pd.read_sql_query(query_currency, conn)
    
    table_curr = Table(title="Fees by Currency (Converted to NOK)", show_header=True, header_style="bold magenta")
    table_curr.add_column("Currency", justify="center")
    table_curr.add_column("Total (NOK)", justify="right")
    
    for _, row in df_currency.iterrows():
        table_curr.add_row(
            row['currency'],
            f"{row['total_fees_nok']:,.2f}"
        )
    console.print(table_curr)
    console.print()

    # 3. Top 10 Largest Fee Transactions
    query_top = """
        SELECT 
            date, 
            type,
            currency, 
            amount_local,
            fee_local,
            fee_currency,
            fee,
            notes
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        ORDER BY (CASE WHEN type = 'FEE' THEN ABS(amount_local) ELSE fee_local END) DESC
        LIMIT 10
    """
    df_top = pd.read_sql_query(query_top, conn)
    
    table_top = Table(title="Top 10 Largest Fees", show_header=True, header_style="bold magenta")
    table_top.add_column("Date", justify="center")
    table_top.add_column("Type")
    table_top.add_column("Notes")
    table_top.add_column("Fee (NOK)", justify="right")
    table_top.add_column("Orig. Fee", justify="right")
    
    for _, row in df_top.iterrows():
        val_nok = abs(row['amount_local']) if row['type'] == 'FEE' else row['fee_local']
        orig_fee = f"{abs(row['amount']):.2f} {row['currency']}" if row['type'] == 'FEE' else f"{row['fee']:.2f} {row.get('fee_currency', '?')}"
        
        table_top.add_row(
            row['date'],
            row['type'],
            row['notes'] or "",
            f"{val_nok:,.2f}",
            orig_fee
        )
    console.print(table_top)
    
    conn.close()

if __name__ == "__main__":
    analyze_fees()
