
import pandas as pd
from datetime import datetime, timedelta
import pyxirr
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.shared.db import get_db_connection
from scripts.analysis.calculations import get_securities_value_on_date, get_portfolio_value_on_date

def final_return_check():
    conn = get_db_connection()
    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    
    # 2021 Invested Capital
    year = 2021
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    
    # 1. Values
    start_val = get_securities_value_on_date(conn, isin_map, start_date - timedelta(days=1))
    end_val = get_securities_value_on_date(conn, isin_map, end_date)
    
    # 2. Flows (Pure Investment)
    c = conn.cursor()
    # Categorization makes this robust!
    c.execute(f"SELECT TradeDate, Amount_NOK FROM transactions WHERE Category IN ('TRADE', 'INCOME') AND strftime('%Y', TradeDate) = '{year}'")
    flows = c.fetchall()
    
    dates = [start_date]
    values = [-start_val]
    for d_str, amt in flows:
        dates.append(pd.to_datetime(d_str))
        values.append(amt)
    
    dates.append(end_date)
    values.append(end_val)
    
    try:
        xirr = pyxirr.xirr(dates, values)
        print(f"--- 2021 INVESTED CAPITAL RETURN ---")
        print(f"Start Value: {start_val:,.2f}")
        print(f"End Value:   {end_val:,.2f}")
        print(f"XIRR:        {xirr:.2%}")
    except Exception as e:
        print(f"Error: {e}")
        
    conn.close()

if __name__ == '__main__':
    final_return_check()
