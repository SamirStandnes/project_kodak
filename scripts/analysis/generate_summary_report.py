import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from collections import deque
import pyxirr

# --- Exchange Rate and Price Functions ---
data_cache = {}

def get_historical_price(ticker_symbol, date):
    cache_key = f"{ticker_symbol}-{date.strftime('%Y-%m-%d')}"
    if cache_key in data_cache:
        return data_cache[cache_key]

    try:
        end_date = date + timedelta(days=1)
        start_date = end_date - timedelta(days=7)
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        if hist.empty:
            data_cache[cache_key] = None
            return None
        price = hist['Close'].iloc[-1]
        data_cache[cache_key] = price
        return price
    except Exception:
        data_cache[cache_key] = None
        return None

def get_latest_exchange_rate(base_currency, target_currency='NOK'):
    if base_currency == target_currency:
        return 1.0
    if base_currency == 'HKD' and target_currency == 'NOK':
        usd_nok_rate = get_latest_exchange_rate('USD', 'NOK')
        hkd_usd_rate = get_latest_exchange_rate('HKD', 'USD')
        if usd_nok_rate and hkd_usd_rate:
            return usd_nok_rate * hkd_usd_rate
        else:
            return None
    ticker = f"{base_currency}{target_currency}=X"
    return get_historical_price(ticker, datetime.today())

# --- Core Calculation Functions ---

def calculate_consolidated_average_wac(conn, isin):
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
    c = conn.cursor()
    c.execute("SELECT TradeDate, Type, Amount_Base FROM transactions WHERE Type IN ('DEPOSIT', 'WITHDRAWAL')")
    transactions = c.fetchall()
    dates, values = [], []
    for trade_date, trans_type, amount_base in transactions:
        if amount_base is not None:
            value = float(amount_base)
            if trans_type == 'DEPOSIT': value = -abs(value)
            else: value = abs(value)
            dates.append(pd.to_datetime(trade_date).date())
            values.append(value)
    dates.append(datetime.today().date())
    values.append(total_market_value)
    valid_dates, valid_values = zip(*[(d, v) for d, v in zip(dates, values) if v != 0])
    if len(valid_values) < 2: return 0.0
    try: return pyxirr.xirr(valid_dates, valid_values)
    except Exception as e:
        print(f"\nCould not calculate Annualized Return (XIRR): {e}")
        return 0.0

# --- Main Report Generation ---

def generate_summary_report(verbose=True):
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    isin_map = pd.read_sql_query("SELECT * FROM isin_symbol_map", conn).set_index('ISIN').to_dict('index')
    c.execute("SELECT ISIN, SUM(Quantity) as Quantity FROM transactions WHERE ISIN IS NOT NULL GROUP BY ISIN HAVING SUM(Quantity) > 0")
    holdings = c.fetchall()

    portfolio_data, unpriced_securities = [], []
    
    for isin, quantity in holdings:
        if isin not in isin_map: continue
        
        mapping_info = isin_map[isin]
        symbol, security_currency = mapping_info['Symbol'], mapping_info['Currency']
        sector, region, country = mapping_info.get('Sector'), mapping_info.get('Region'), mapping_info.get('Country')

        avg_wac_nok = calculate_consolidated_average_wac(conn, isin)
        fifo_wac_nok = calculate_consolidated_fifo_wac(conn, isin)
        
        price_local = get_historical_price(symbol, datetime.today())
        price_nok = 0

        if price_local is not None and price_local > 0:
            if security_currency == 'NOK':
                price_nok = price_local
            else:
                rate = get_latest_exchange_rate(security_currency)
                if rate is not None and rate > 0:
                    price_nok = price_local * rate
        
        if price_nok == 0: unpriced_securities.append(f"{symbol} ({isin})")

        market_value = price_nok * quantity
        avg_cost_basis = avg_wac_nok * quantity
        fifo_cost_basis = fifo_wac_nok * quantity
        
        portfolio_data.append({
            "Symbol": symbol, "Quantity": quantity, "Sector": sector, "Region": region, "Country": country,
            "AvgWAC_NOK": avg_wac_nok, "FIFOWAC_NOK": fifo_wac_nok, "MarketValue_NOK": market_value,
            "AvgReturn_pct": (market_value / avg_cost_basis - 1) * 100 if avg_cost_basis > 0 else 0,
            "FIFOReturn_pct": (market_value / fifo_cost_basis - 1) * 100 if fifo_cost_basis > 0 else 0,
            "AvgCostBasis_NOK": avg_cost_basis, "FIFOCostBasis_NOK": fifo_cost_basis,
        })

    if not portfolio_data:
        conn.close()
        return pd.DataFrame(), {}, []

    df = pd.DataFrame(portfolio_data)
    df = df.sort_values(by="MarketValue_NOK", ascending=False).reset_index(drop=True)
    
    total_market_value = df["MarketValue_NOK"].sum()
    if total_market_value > 0: df['Weight'] = df['MarketValue_NOK'] / total_market_value
    else: df['Weight'] = 0

    total_avg_cost_basis = df["AvgCostBasis_NOK"].sum()
    total_fifo_cost_basis = df["FIFOCostBasis_NOK"].sum()
    
    c.execute("SELECT Type, SUM(Amount_Base) FROM transactions WHERE Type IN ('FEE', 'DIVIDEND', 'INTEREST') GROUP BY Type")
    other_sums = dict(c.fetchall())
    total_fees = abs(other_sums.get('FEE', 0))
    total_dividends = other_sums.get('DIVIDEND', 0)
    total_interest_paid = abs(other_sums.get('INTEREST', 0))

    cagr_xirr = calculate_xirr(conn, total_market_value, verbose=verbose)
    
    # All calculations done, now assemble the summary and close the connection
    summary_data = {
        "total_market_value": total_market_value,
        "total_avg_gain_loss": total_market_value - total_avg_cost_basis,
        "total_avg_return_pct": (total_market_value / total_avg_cost_basis - 1) * 100 if total_avg_cost_basis > 0 else 0,
        "total_fifo_gain_loss": total_market_value - total_fifo_cost_basis,
        "total_fifo_return_pct": (total_market_value / total_fifo_cost_basis - 1) * 100 if total_fifo_cost_basis > 0 else 0,
        "total_fees": total_fees, "total_dividends": total_dividends, "total_interest_paid": total_interest_paid,
        "cagr_xirr": cagr_xirr,
    }
    
    conn.close()
    return df, summary_data, []

if __name__ == '__main__':
    main_df, summary, unpriced = generate_summary_report()
    if not main_df.empty:
        print("--- Report Generation Successful ---")
        # Keep output minimal for this test
    else:
        print("--- Report Generation Failed: No data ---")
