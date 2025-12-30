
import sqlite3
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import pyxirr

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.analysis.calculations import get_securities_value_on_date
from scripts.shared.db import get_db_connection
from scripts.shared.utils import parse_date_flexible

def debug_2022_invested():
    conn = get_db_connection()
    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    
    year = 2022
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    
    print(f"--- Debugging 2022 Invested Return ---")
    
    # 1. Start Value
    start_val = get_securities_value_on_date(conn, isin_map, start_date - timedelta(days=1))
    print(f"Start Value (Securities Dec 31, 2021): {start_val:,.2f}")
    
    # 2. End Value
    end_val = get_securities_value_on_date(conn, isin_map, end_date)
    print(f"End Value   (Securities Dec 31, 2022): {end_val:,.2f}")
    
    # 3. Cash Flows (Current Logic)
    c = conn.cursor()
    c.execute(f"""
        SELECT TradeDate, Type, Amount_Base, Symbol 
        FROM transactions 
        WHERE Type IN ('BUY', 'SELL', 'DIVIDEND') 
        AND strftime('%Y', TradeDate) = '{year}'
        ORDER BY TradeDate
    """)
    rows = c.fetchall()
    
    print(f"\n--- Cash Flows (BUY/SELL/DIVIDEND) ---")
    dates = [start_date]
    values = [-start_val]
    
    total_in = 0
    total_out = 0
    
    for date_str, t_type, amount, sym in rows:
        d = parse_date_flexible(date_str)
        print(f"{date_str} | {t_type:<10} | {sym:<15} | {amount:>10.2f}")
        if d:
            dates.append(d)
            values.append(amount)
            if amount < 0: total_in += -amount
            else: total_out += amount

    # 4. Check for TRANSFERS (Potential Missing Data)
    print(f"\n--- Check for TRANSFERS (Currently Ignored) ---")
    c.execute(f"""
        SELECT TradeDate, Type, Quantity, Price, Symbol 
        FROM transactions 
        WHERE Type IN ('TRANSFER_IN', 'TRANSFER_OUT') 
        AND strftime('%Y', TradeDate) = '{year}'
    """)
    transfers = c.fetchall()
    for date_str, t_type, qty, price, sym in transfers:
        qty_val = qty if qty else 0
        price_val = price if price else 0
        val = qty_val * price_val
        sym_str = str(sym) if sym else "N/A"
        print(f"[ALERT] {date_str} | {t_type:<12} | {sym_str:<15} | Qty: {qty_val} | Price: {price_val} | Approx Val: {val}")

    dates.append(end_date)
    values.append(end_val)
    
    try:
        xirr = pyxirr.xirr(dates, values)
        print(f"\nCALCULATED XIRR: {xirr:.2%}")
    except Exception as e:
        print(f"\nCALCULATION FAILED: {e}")

    conn.close()

if __name__ == '__main__':
    debug_2022_invested()
