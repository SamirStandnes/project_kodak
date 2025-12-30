import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pyxirr
import sys
import os
from rich.console import Console
from rich.table import Table

# Add the parent directory of 'scripts' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.analysis.utils import parse_date_flexible, get_historical_price, get_historical_exchange_rate

def get_holdings_on_date(conn, target_date):
    """
    Calculates the quantity of each ISIN held on a specific date.
    """
    print(f"\n--- Querying for holdings on or before {target_date.strftime('%Y-%m-%d')} ---")
    target_date_obj = pd.to_datetime(target_date)
    query = f"SELECT ISIN, Type, Quantity FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("  - No transactions found.")
        return pd.Series(dtype='float64')

    print(f"  - Found {len(df)} transactions to process.")
    buy_types = ['BUY', 'TRANSFER_IN', 'STOCK_SPLIT']
    sell_types = ['SELL', 'TRANSFER_OUT']

    def adjust_quantity(row):
        qty = row['Quantity']
        if row['Type'] in buy_types:
            return abs(qty)
        elif row['Type'] in sell_types:
            return -abs(qty)
        return 0

    df['AdjustedQuantity'] = df.apply(adjust_quantity, axis=1)
    
    holdings = df.groupby('ISIN')['AdjustedQuantity'].sum()
    final_holdings = holdings[holdings > 0]
    print(f"  - Calculated {len(final_holdings)} final holdings with quantity > 0.")
    return final_holdings

def get_cash_balance_on_date(conn, target_date):
    """
    Calculates the cash balance (NOK) on a specific date by summing all transaction amounts.
    """
    target_date_obj = pd.to_datetime(target_date)
    query = f"SELECT SUM(Amount_Base) FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    return result if result is not None else 0.0

def get_portfolio_value_on_date(conn, isin_map, target_date):
    """
    Calculates the total market value of the portfolio on a specific historical date.
    """
    holdings = get_holdings_on_date(conn, target_date)
    securities_value = 0.0

    print(f"\n--- Calculating portfolio value for {target_date.strftime('%Y-%m-%d')} ---")
    if holdings.empty:
        print("  - No holdings to value.")
    else:
        print(f"Found {len(holdings)} holdings to value:")
        print(holdings.to_string())


    for isin, quantity in holdings.items():
        if isin not in isin_map:
            print(f"  - Warning: ISIN {isin} not found in isin_map. Skipping.")
            continue
            
        mapping_info = isin_map[isin]
        symbol, security_currency = mapping_info['Symbol'], mapping_info['Currency']
        
        # Try to get market price first
        price_local = get_historical_price(symbol, target_date)
        
        # Fallback: If no market price (e.g. Funds), use the last transaction price (Cost Basis)
        if price_local is None or price_local == 0:
            last_trans_query = f"""
                SELECT Price, Currency_Local FROM transactions 
                WHERE ISIN = '{isin}' 
                AND TradeDate <= '{target_date.strftime('%Y-%m-%d %H:%M:%S')}' 
                AND Price > 0
                ORDER BY TradeDate DESC LIMIT 1
            """
            cursor = conn.cursor()
            cursor.execute(last_trans_query)
            result = cursor.fetchone()
            if result:
                price_local, trans_currency = result
                if trans_currency and trans_currency != security_currency:
                    security_currency = trans_currency
                print(f"    - [Fallback] Using transaction price: {price_local} {security_currency}")

        print(f"\n  - Valuing {symbol} ({isin})...")
        print(f"    - Quantity: {quantity:.4f}")
        
        price_local = get_historical_price(symbol, target_date)
        price_nok = 0

        if price_local is not None and price_local > 0:
            print(f"    - Historical price in {security_currency}: {price_local:,.2f}")
            if security_currency == 'NOK':
                price_nok = price_local
            else:
                rate = get_historical_exchange_rate(security_currency, 'NOK', target_date)
                if rate is not None and rate > 0:
                    print(f"    - Historical exchange rate ({security_currency}/NOK): {rate:,.4f}")
                    price_nok = price_local * rate
                else:
                    print(f"    - Could not fetch exchange rate for {security_currency}/NOK.")
        
        if price_nok > 0:
            value = price_nok * quantity
            securities_value += value
            print(f"    - Calculated Value (NOK): {value:,.2f}")
        else:
            print(f"    - Could not price this holding in NOK.")
            
    # Add Cash Balance
    cash_value = get_cash_balance_on_date(conn, target_date)
    print(f"\n  - Cash Balance (Simulated): {cash_value:,.2f} NOK")
    
    total_value = securities_value + cash_value
    print(f"--- Total portfolio value for {target_date.strftime('%Y-%m-%d')}: {total_value:,.2f} NOK ---")
    return total_value

def debug_year(year):
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    console = Console()

    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')

    console.print(f"\n[bold magenta]--- Debugging XIRR Calculation for {year} ---[/bold magenta]")
    
    start_of_year = datetime(year, 1, 1)
    # Get EOD value for the day before the start of the year
    start_value = get_portfolio_value_on_date(conn, isin_map, start_of_year - timedelta(days=1))

    end_of_year_date = datetime(year, 12, 31)
    # For the current year, use today's date if it's earlier than Dec 31
    if year == datetime.now().year:
        end_of_year_date = datetime.now()
    end_value = get_portfolio_value_on_date(conn, isin_map, end_of_year_date)
    
    c.execute("""
        SELECT TradeDate, Amount_Base, Type FROM transactions 
        WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') AND STRFTIME('%Y', TradeDate) = ?
        ORDER BY TradeDate
    """, (str(year),))
    cash_flows = c.fetchall()
    
    dates = [start_of_year]
    values = [-start_value] # Initial investment for the period (outflow)
    
    print("\n--- Assembling cash flows for XIRR calculation ---")
    print(f"  - {start_of_year.strftime('%Y-%m-%d')}: Starting Value (as outflow): [yellow]{-start_value:,.2f} NOK[/yellow]")

    for date_str, amount, trans_type in cash_flows:
        flow_date = parse_date_flexible(date_str)
        # In XIRR, money in (DEPOSIT) is negative, money out (WITHDRAWAL) is positive
        # Since Amount_Base is + for Deposit and - for Withdrawal in DB,
        # we simply negate it to get the correct XIRR flow direction.
        flow_amount = -amount 
        if flow_date:
            dates.append(flow_date)
            values.append(flow_amount)
            print(f"  - {flow_date.strftime('%Y-%m-%d')}: {trans_type}: [yellow]{flow_amount:,.2f} NOK[/yellow]")
        else:
            print(f"[red]Warning: Could not parse date for cash flow: {date_str}[/red]")

    dates.append(end_of_year_date)
    values.append(end_value) # Final value of the period (inflow)
    print(f"  - {end_of_year_date.strftime('%Y-%m-%d')}: Ending Value (as inflow): [yellow]{end_value:,.2f} NOK[/yellow]")
    print("[bold]--- Done assembling cash flows ---[/bold]\n")

    try:
        # Filter out None dates which can result from parsing errors (though parse_date_flexible should minimize this)
        valid_indices = [i for i, d in enumerate(dates) if d is not None]
        valid_dates = [dates[i] for i in valid_indices]
        valid_values = [values[i] for i in valid_indices]

        if len(valid_dates) < 2:
            console.print(f"[bold red]Not enough valid data points for XIRR calculation for {year}.[/bold red]")
            annual_return = 0.0
        else:
            annual_return = pyxirr.xirr(valid_dates, valid_values)
        
        console.print(f"[bold green]Final Calculated Return for {year}: {annual_return:.2%}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error calculating XIRR for {year}: {e}[/bold red]")

    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python debug_yearly_return.py <year>")
        sys.exit(1)
        
    try:
        target_year = int(sys.argv[1])
        debug_year(target_year)
    except ValueError:
        print("Error: Please provide a valid year.")
        sys.exit(1)