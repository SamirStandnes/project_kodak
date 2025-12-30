import sqlite3
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.analysis.calculations import get_securities_value_on_date, get_holdings_on_date

def debug_v2_start_val():
    conn = sqlite3.connect('database/portfolio.db')
    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    
    date = datetime(2020, 12, 31)
    print(f"--- V2 Audit: Holdings on {date.date()} ---")
    holdings = get_holdings_on_date(conn, date)
    print(holdings)
    
    val = get_securities_value_on_date(conn, isin_map, date)
    print(f"\nFinal Securities Value: {val:,.2f} NOK")
    conn.close()

if __name__ == '__main__':
    debug_v2_start_val()

