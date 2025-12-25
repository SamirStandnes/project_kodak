from collections import deque
from datetime import datetime
import pyxirr
from scripts.analysis.utils import parse_date_flexible

def calculate_consolidated_average_wac(conn, isin):
    """
    Calculates the Average Weighted Average Cost (WAC) for a given ISIN across all accounts.
    Returns the average cost per share in NOK.
    """
    c = conn.cursor()
    c.execute("SELECT Quantity, Price, ExchangeRate, Currency_Local FROM transactions WHERE ISIN = ? AND Type IN ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT') AND Quantity > 0", (isin,))
    transactions = c.fetchall()
    total_cost_nok, total_quantity = 0, 0
    for quantity, price, exchange_rate_str, currency_local in transactions:
        cost_nok = 0
        if currency_local == 'NOK': cost_nok = quantity * price
        elif exchange_rate_str is not None:
            try:
                exchange_rate = float(str(exchange_rate_str).replace(',', '.'))
                if exchange_rate != 0: cost_nok = quantity * price * exchange_rate
            except (ValueError, AttributeError): pass 
        total_cost_nok += cost_nok
        total_quantity += quantity
    return total_cost_nok / total_quantity if total_quantity > 0 else 0

def calculate_consolidated_fifo_wac(conn, isin):
    """
    Calculates the FIFO Weighted Average Cost (WAC) for a given ISIN across all accounts.
    Returns the average cost per share of the remaining holdings in NOK.
    """
    c = conn.cursor()
    c.execute("SELECT Quantity, Price, ExchangeRate, Currency_Local, Type, TradeDate FROM transactions WHERE ISIN = ? AND Type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT', 'STOCK_SPLIT') ORDER BY TradeDate, GlobalID", (isin,))
    transactions = c.fetchall()
    buy_lots = deque()
    for quantity, price, exchange_rate_str, currency_local, trans_type, trade_date in transactions:
        if trans_type in ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT'):
            cost_nok = 0
            if currency_local == 'NOK': cost_nok = quantity * price
            elif exchange_rate_str is not None:
                try:
                    exchange_rate = float(str(exchange_rate_str).replace(',', '.'))
                    if exchange_rate != 0: cost_nok = quantity * price * exchange_rate
                except (ValueError, AttributeError): pass 
            buy_lots.append({'quantity': quantity, 'cost_per_share_nok': cost_nok / quantity if quantity > 0 else 0})
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

def calculate_xirr(conn, total_market_value, verbose=False):
    """
    Calculates the XIRR for the entire portfolio given the current total market value.
    """
    c = conn.cursor()
    c.execute("SELECT TradeDate, Type, Amount_Base FROM transactions WHERE Type IN ('DEPOSIT', 'WITHDRAWAL')")
    transactions = c.fetchall()
    dates, values = [], []
    for trade_date, trans_type, amount_base in transactions:
        date_obj = parse_date_flexible(trade_date)
        if amount_base is not None and date_obj:
            value = float(amount_base)
            if trans_type == 'DEPOSIT': value = -abs(value)
            else: value = abs(value)
            dates.append(date_obj.date())
            values.append(value)
    dates.append(datetime.today().date())
    values.append(total_market_value)
    if len(values) < 2: return 0.0
    # Ensure there's at least one non-zero cashflow to avoid errors
    if not any(v for v in values[:-1]): return 0.0
    try: return pyxirr.xirr(dates, values)
    except Exception as e:
        if verbose:
            print(f"\nCould not calculate Annualized Return (XIRR): {e}")
        return 0.0
