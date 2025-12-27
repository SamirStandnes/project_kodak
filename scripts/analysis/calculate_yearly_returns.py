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

from scripts.analysis.utils import parse_date_flexible
from scripts.analysis.calculations import (
    get_portfolio_value_on_date, 
    get_securities_value_on_date, 
    get_cash_balance_on_date
)

def calculate_yearly_returns(invested_only=False):
    """
    Calculates the annual return (XIRR) for each year in the transaction history.
    If invested_only=True, it ignores cash balances and calculates return on Invested Capital.
    """
    # Construct absolute path to the database
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    
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
    if start_year < 2020:
        start_year = 2020
    end_year = parse_date_flexible(max_date_str).year
    
    yearly_returns = []

    for year in range(start_year, end_year + 1):
        # print(f"Calculating return for {year} (Invested Only: {invested_only})...")
        
        start_of_year = datetime(year, 1, 1)
        # For the current year, use today's date if it's earlier than Dec 31
        end_of_year = datetime(year, 12, 31)
        if year == datetime.now().year:
            end_of_year = datetime.now()

        if invested_only:
            # 1. Start Value: Securities Only
            start_value = get_securities_value_on_date(conn, isin_map, start_of_year - timedelta(days=1))
            # 2. End Value: Securities Only
            end_value = get_securities_value_on_date(conn, isin_map, end_of_year)
            
            c.execute("""
                SELECT TradeDate, Amount_Base FROM transactions 
                WHERE Type IN ('BUY', 'SELL', 'DIVIDEND') 
                AND STRFTIME('%Y', TradeDate) = ?
            """, (str(year),))
            cash_flows = c.fetchall()
            
        else:
            # Standard Portfolio Return
            start_value = get_portfolio_value_on_date(conn, isin_map, start_of_year - timedelta(days=1)) 
            end_value = get_portfolio_value_on_date(conn, isin_map, end_of_year)
            
            c.execute("""
                SELECT TradeDate, Amount_Base FROM transactions 
                WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') AND STRFTIME('%Y', TradeDate) = ?
            """, (str(year),))
            cash_flows = c.fetchall()
        
        # 4. Assemble dates and values for XIRR
        dates = [start_of_year]
        values = [-start_value] # Initial investment for the period
        
        for date_str, amount in cash_flows:
            d = parse_date_flexible(date_str)
            if d:
                dates.append(d)
                if invested_only:
                    values.append(amount) 
                else:
                    values.append(-amount)

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

def calculate_rolling_returns():
    """
    Calculates XIRR for rolling periods: YTD, 1Y, 3Y, 5Y, All Time.
    """
    # Construct absolute path to the database
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    
    today = datetime.now()
    periods = {
        'YTD': datetime(today.year, 1, 1),
        '1Y': today - timedelta(days=365),
        '3Y': today - timedelta(days=3*365),
        '5Y': today - timedelta(days=5*365),
        'All Time': None # Will handle separately
    }
    
    results = {}
    
    # Get current portfolio value (End Value)
    end_value = get_portfolio_value_on_date(conn, isin_map, today)
    
    # Get earliest transaction date for 'All Time'
    c.execute("SELECT MIN(TradeDate) FROM transactions")
    min_date_str = c.fetchone()[0]
    if min_date_str:
        periods['All Time'] = parse_date_flexible(min_date_str)
    
    for label, start_date in periods.items():
        if start_date is None or start_date > today:
            results[label] = None
            continue
            
        print(f"Calculating {label} return (since {start_date.date()})...")
        
        if label == 'All Time':
            # Special handling for All Time: Start Value is 0, include ALL cash flows
            # This ensures we don't miss the initial deposit or double-count it
            start_value = 0.0
            c.execute(f"""
                SELECT TradeDate, Amount_Base FROM transactions 
                WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') 
                AND TradeDate <= ?
            """, (today.strftime('%Y-%m-%d %H:%M:%S'),))
        else:
            # For specific windows (YTD, 1Y), Start Value is the portfolio value at that time
            start_value = get_portfolio_value_on_date(conn, isin_map, start_date)
            # Cash flows strictly AFTER the start date
            c.execute(f"""
                SELECT TradeDate, Amount_Base FROM transactions 
                WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') 
                AND TradeDate > ? AND TradeDate <= ?
            """, (start_date.strftime('%Y-%m-%d %H:%M:%S'), today.strftime('%Y-%m-%d %H:%M:%S')))
        
        cash_flows = c.fetchall()
        
        # 3. Setup XIRR
        dates = [start_date]
        values = [-start_value] # Initial Investment
        
        for date_str, amount in cash_flows:
            d = parse_date_flexible(date_str)
            if d:
                dates.append(d)
                values.append(-amount) # -Deposit, +Withdrawal
                
        dates.append(today)
        values.append(end_value)
        
        try:
            # For All Time, remove the dummy 0.0 start value if it exists at index 0
            if label == 'All Time':
                dates.pop(0)
                values.pop(0)
                
            if len(dates) < 2:
                xirr = 0.0
            else:
                xirr = pyxirr.xirr(dates, values)
        except Exception:
            xirr = None
            
        results[label] = xirr
        
    conn.close()
    return results

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
        
    # Test Rolling
    rolling = calculate_rolling_returns()
    console.print(rolling)