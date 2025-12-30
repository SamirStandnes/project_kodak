
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pyxirr
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.analysis.calculations import get_portfolio_value_on_date
from scripts.shared.db import get_db_connection
from scripts.shared.utils import parse_date_flexible

def debug_2021_full():
    conn = get_db_connection()
    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    
    year = 2021
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    
    start_val = get_portfolio_value_on_date(conn, isin_map, start_date - timedelta(days=1))
    end_val = get_portfolio_value_on_date(conn, isin_map, end_date)
    
    c = conn.cursor()
    c.execute(f"""
        SELECT TradeDate, Type, Amount_Base, Symbol 
        FROM transactions 
        WHERE Type IN ('DEPOSIT', 'WITHDRAWAL') 
        AND strftime('%Y', TradeDate) = '{year}'
        ORDER BY TradeDate
    """)
    flows = c.fetchall()
    
    print(f"--- XIRR INPUTS FOR 2021 ---")
    print(f"START: {start_date.date()} | {-start_val:>12.2f} (Start Value)")
    
    dates = [start_date]
    values = [-start_val]
    
    for d_str, t_type, amt, sym in flows:
        d = parse_date_flexible(d_str)
        val = -amt # Invert because Deposit (+) is an investment outflow (-)
        dates.append(d)
        values.append(val)
        print(f"FLOW : {d.date()} | {val:>12.2f} ({t_type})")
        
    print(f"END  : {end_date.date()} | {end_val:>12.2f} (End Value)")
    values.append(end_val)
    dates.append(end_date)
    
    xirr = pyxirr.xirr(dates, values)
    print(f"\nFINAL XIRR: {xirr:.2%}")
    conn.close()

if __name__ == '__main__':
    debug_2021_full()
