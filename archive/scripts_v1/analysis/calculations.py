from collections import deque
from datetime import datetime, timedelta
import pyxirr
import pandas as pd

# Import from shared modules
from scripts.shared.utils import parse_date_flexible
from scripts.shared.market_data import get_historical_price, get_exchange_rate

def calculate_consolidated_average_wac(conn, isin):
    c = conn.cursor()
    c.execute("SELECT Quantity, Price, ExchangeRate, Currency_Raw, Amount_NOK FROM transactions WHERE ISIN = ? AND Type IN ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT') AND Quantity > 0", (isin,))
    transactions = c.fetchall()
    total_cost_nok, total_quantity = 0, 0
    for quantity, price, rate, curr_raw, amt_nok in transactions:
        total_cost_nok += abs(amt_nok)
        total_quantity += quantity
    return total_cost_nok / total_quantity if total_quantity > 0 else 0

def calculate_consolidated_fifo_wac(conn, isin):
    c = conn.cursor()
    c.execute("SELECT Quantity, Price, ExchangeRate, Currency_Raw, Type, TradeDate, Amount_NOK FROM transactions WHERE ISIN = ? AND Type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT', 'STOCK_SPLIT') ORDER BY TradeDate, GlobalID", (isin,))
    transactions = c.fetchall()
    buy_lots = deque()
    for quantity, price, rate, curr_raw, trans_type, trade_date, amt_nok in transactions:
        if trans_type in ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT'):
            cost_per_share = abs(amt_nok) / quantity if quantity > 0 else 0
            buy_lots.append({'quantity': quantity, 'cost_per_share_nok': cost_per_share})
        elif trans_type in ('SELL', 'TRANSFER_OUT'):
            sell_quantity = abs(quantity)
            while sell_quantity > 0 and buy_lots:
                oldest_lot = buy_lots[0]
                if oldest_lot['quantity'] <= sell_quantity:
                    sell_quantity -= oldest_lot['quantity']
                    buy_lots.popleft()
                else:
                    oldest_lot['quantity'] -= sell_quantity
                    sell_quantity = 0
    total_cost_nok, total_quantity = 0, 0
    for lot in buy_lots:
        total_cost_nok += lot['quantity'] * lot['cost_per_share_nok']
        total_quantity += lot['quantity']
    return total_cost_nok / total_quantity if total_quantity > 0 else 0

def calculate_xirr(conn, total_market_value, current_cash_balance=0.0, verbose=False):
    c = conn.cursor()
    c.execute("SELECT TradeDate, Type, Amount_NOK FROM transactions WHERE Category = 'CASH_FLOW'")
    transactions = c.fetchall()
    dates, values = [], []
    for trade_date, trans_type, amt_nok in transactions:
        date_obj = parse_date_flexible(trade_date)
        if amt_nok is not None and date_obj:
            values.append(-amt_nok)
            dates.append(date_obj.date())
    dates.append(datetime.today().date())
    total_account_value = total_market_value + current_cash_balance
    values.append(total_account_value)
    if len(values) < 2 or not any(v for v in values[:-1]): return 0.0
    try: return pyxirr.xirr(dates, values)
    except Exception as e:
        if verbose: print(f"XIRR Error: {e}")
        return 0.0

def get_holdings_on_date(conn, target_date):
    target_date_obj = pd.to_datetime(target_date)
    query = f"SELECT ISIN, SUM(Quantity) as NetQuantity FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}' AND ISIN IS NOT NULL GROUP BY ISIN HAVING ABS(SUM(Quantity)) > 0.0001"
    df = pd.read_sql_query(query, conn)
    return df.set_index('ISIN')['NetQuantity'] if not df.empty else pd.Series(dtype=float)

def get_cash_balance_on_date(conn, target_date):
    target_date_obj = pd.to_datetime(target_date)
    query = f"SELECT SUM(Amount_NOK) FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    return result if result is not None else 0.0

def get_securities_value_on_date(conn, isin_map, target_date):
    holdings = get_holdings_on_date(conn, target_date)
    securities_value = 0.0
    for isin, quantity in holdings.items():
        if isin not in isin_map: continue
        info = isin_map[isin]
        symbol, security_currency = info['Symbol'], info['Currency']
        price_local = get_historical_price(symbol, target_date, isin=isin, conn=conn)
        if price_local is None or price_local == 0:
            last_trans_query = f"SELECT Price, Currency_Raw FROM transactions WHERE ISIN = '{isin}' AND TradeDate <= '{target_date.strftime('%Y-%m-%d %H:%M:%S')}' AND Price > 0 ORDER BY TradeDate DESC LIMIT 1"
            cursor = conn.cursor()
            cursor.execute(last_trans_query)
            res = cursor.fetchone()
            if res:
                price_local, trans_currency = res
                if trans_currency: security_currency = trans_currency
        price_nok = 0
        if price_local and price_local > 0:
            if security_currency == 'NOK': price_nok = price_local
            else:
                rate = get_exchange_rate(security_currency, 'NOK', target_date)
                if rate: price_nok = price_local * rate
        if price_nok > 0: securities_value += price_nok * quantity
    return securities_value

def get_portfolio_value_on_date(conn, isin_map, target_date):
    return get_securities_value_on_date(conn, isin_map, target_date) + get_cash_balance_on_date(conn, target_date)
