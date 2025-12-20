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
    # Ensure target_date is a datetime object
    target_date_obj = pd.to_datetime(target_date)
    
    # Query all relevant transactions up to the target date
    query = f"SELECT ISIN, Type, Quantity FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    df = pd.read_sql_query(query, conn)
    
    # Calculate current holdings by summing up quantities
    # Ensure BUYs are positive and SELLs are negative, regardless of how they are stored in DB
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
    
    # Filter out securities with zero or negative quantity
    return holdings[holdings > 0]

def get_cash_balance_on_date(conn, target_date):
    """
    Calculates the cash balance (NOK) on a specific date by summing all transaction amounts.
    Positive Cash = Asset. Negative Cash = Margin Debt.
    """
    target_date_obj = pd.to_datetime(target_date)
    query = f"SELECT SUM(Amount_Base) FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    return result if result is not None else 0.0

def get_portfolio_value_on_date(conn, isin_map, target_date):
    """
    Calculates the total market value of the portfolio (Securities + Cash) on a specific historical date.
    """
    # 1. Securities Value
    holdings = get_holdings_on_date(conn, target_date)
    securities_value = 0.0

    for isin, quantity in holdings.items():
        if isin not in isin_map:
            continue
            
        mapping_info = isin_map[isin]
        symbol, security_currency = mapping_info['Symbol'], mapping_info['Currency']
        
        # Try to get market price first
        price_local = get_historical_price(symbol, target_date)
        
        # Fallback: If no market price (e.g. Funds), use the last transaction price (Cost Basis)
        if price_local is None or price_local == 0:
            # Find the most recent transaction for this ISIN before the target date
            # We filter for positive price to ensure we get a valid valuation marker
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
                # Update currency if needed (though usually matches security_currency)
                if trans_currency and trans_currency != security_currency:
                    security_currency = trans_currency
                # print(f"  -> Using fallback price for {symbol}: {price_local} {security_currency}") # Debug

        price_nok = 0

        if price_local is not None and price_local > 0:
            if security_currency == 'NOK':
                price_nok = price_local
            else:
                rate = get_historical_exchange_rate(security_currency, 'NOK', target_date)
                if rate is not None and rate > 0:
                    price_nok = price_local * rate
        
        if price_nok > 0:
            securities_value += price_nok * quantity
            
    # 2. Cash Value (includes Margin Debt as negative cash)
    cash_value = get_cash_balance_on_date(conn, target_date)
    
    return securities_value + cash_value

def calculate_yearly_returns():
    """
    Calculates the annual return (XIRR) for each year in the transaction history.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')

    # Find the range of years in the data
    c.execute("SELECT MIN(TradeDate), MAX(TradeDate) FROM transactions")
    min_date_str, max_date_str = c.fetchone()
    
    if not min_date_str:
        print("No transactions found in the database.")
        return []

    start_year = parse_date_flexible(min_date_str).year
    end_year = parse_date_flexible(max_date_str).year
    
    yearly_returns = []

    for year in range(start_year, end_year + 1):
        print(f"Calculating return for {year}...")
        
        # 1. Get portfolio value at the start of the year
        start_of_year = datetime(year, 1, 1)
        start_value = get_portfolio_value_on_date(conn, isin_map, start_of_year - timedelta(days=1)) # Use day before for EOD value

        # 2. Get portfolio value at the end of the year
        end_of_year = datetime(year, 12, 31)
        # For the current year, use today's date if it's earlier than Dec 31
        if year == datetime.now().year:
            end_of_year = datetime.now()
        end_value = get_portfolio_value_on_date(conn, isin_map, end_of_year)
        
        # 3. Get all cash flows during the year
        c.execute("""
            SELECT TradeDate, Amount_Base FROM transactions 
            WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') AND STRFTIME('%Y', TradeDate) = ?
        """, (str(year),))
        
        cash_flows = c.fetchall()
        
        # 4. Assemble dates and values for XIRR
        dates = [start_of_year]
        values = [-start_value] # Initial investment for the period
        
        for date_str, amount in cash_flows:
            dates.append(parse_date_flexible(date_str))
            values.append(-amount) # DEPOSIT is cash in to portfolio (-ve), WITHDRAWAL is cash out (+ve)

        dates.append(end_of_year)
        values.append(end_value) # Final value of the period

        # Calculate XIRR
        try:
            # Filter out None dates which can result from parsing errors
            valid_indices = [i for i, d in enumerate(dates) if d is not None]
            valid_dates = [dates[i] for i in valid_indices]
            valid_values = [values[i] for i in valid_indices]

            if len(valid_dates) < 2:
                annual_return = 0.0
            else:
                annual_return = pyxirr.xirr(valid_dates, valid_values)
        except Exception:
            annual_return = None # Indicate failure to calculate

        yearly_returns.append({"Year": year, "Return": annual_return})

    conn.close()
    return yearly_returns


if __name__ == '__main__':
    console = Console()
    results = calculate_yearly_returns()
    
    if results:
        table = Table(title="Yearly Portfolio Returns", show_header=True, header_style="bold magenta")
        table.add_column("Year", style="cyan", justify="center")
        table.add_column("Annual Return (XIRR)", justify="right")
        
        for result in results:
            return_str = f"{result['Return']:.2%}" if result['Return'] is not None else "[red]N/A[/red]"
            table.add_row(str(result['Year']), return_str)
            
        console.print(table)
