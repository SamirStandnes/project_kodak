from collections import deque
from datetime import datetime, timedelta
import pyxirr
import pandas as pd
from scripts.analysis.utils import parse_date_flexible, get_historical_price, get_historical_exchange_rate

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

def calculate_xirr(conn, total_market_value, current_cash_balance=0.0, verbose=False):
    """
    Calculates the XIRR for the entire portfolio given the current total market value and cash balance.
    End Value = Securities Value + Cash Balance (Net Equity).
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
    
    # Net Equity = Asset Value + Cash Balance (which is negative for margin)
    total_account_value = total_market_value + current_cash_balance
    values.append(total_account_value)
    
    if len(values) < 2: return 0.0
    # Ensure there's at least one non-zero cashflow to avoid errors
    if not any(v for v in values[:-1]): return 0.0
    try: return pyxirr.xirr(dates, values)
    except Exception as e:
        if verbose:
            print(f"\nCould not calculate Annualized Return (XIRR): {e}")
        return 0.0

def get_holdings_on_date(conn, target_date):
    """
    Calculates the quantity of each ISIN held on a specific date.
    """
    # Ensure target_date is a datetime object
    target_date_obj = pd.to_datetime(target_date)
    
    # Query all relevant transactions up to the target date
    query = f"SELECT ISIN, Type, Quantity FROM transactions WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'"
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        return pd.Series(dtype=float)

    # Calculate current holdings by summing up quantities
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
    
    return holdings[holdings > 0.0001]

def get_cash_balance_on_date(conn, target_date):
    """
    Calculates the cash balance (NOK) on a specific date by summing transaction amounts per currency 
    and converting to NOK using the exchange rate ON THAT DATE.
    """
    target_date_obj = pd.to_datetime(target_date)
    
    # Sum Amount_Base grouped by Currency_Base up to target_date
    query = f"""
        SELECT Currency_Base, SUM(Amount_Base) 
        FROM transactions 
        WHERE TradeDate <= '{target_date_obj.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY Currency_Base
    """
    cursor = conn.cursor()
    cursor.execute(query)
    balances = cursor.fetchall()
    
    total_cash_nok = 0.0
    
    for currency, amount in balances:
        if not amount or amount == 0:
            continue
            
        currency = currency.strip().upper() if currency else 'NOK'
        
        if currency == 'NOK':
            total_cash_nok += amount
        else:
            # Convert foreign currency cash balance to NOK using rate at target_date
            rate = get_historical_exchange_rate(currency, 'NOK', target_date_obj)
            if rate is not None and rate > 0:
                total_cash_nok += amount * rate
                
    return total_cash_nok

def get_securities_value_on_date(conn, isin_map, target_date):
    """
    Calculates the total market value of the SECURITIES only on a specific historical date.
    Excludes cash balance.
    """
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
            
    return securities_value

def get_portfolio_value_on_date(conn, isin_map, target_date):
    """
    Calculates the total market value of the portfolio (Securities + Cash) on a specific historical date.
    """
    securities_value = get_securities_value_on_date(conn, isin_map, target_date)
    cash_value = get_cash_balance_on_date(conn, target_date)
    
    return securities_value + cash_value
