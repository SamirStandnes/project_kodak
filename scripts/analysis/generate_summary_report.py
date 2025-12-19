import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from collections import deque
import pyxirr

# --- Date Parsing Helper ---
def parse_date_flexible(date_string):
    """
    Parses a date string that could be in one of several formats.
    """
    if not date_string:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None # Return None if no format matches

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

        price_local = get_historical_price(symbol, datetime.today())
        price_nok = 0

        if price_local is not None and price_local > 0:
            if security_currency == 'NOK':
                price_nok = price_local
            else:
                rate = get_latest_exchange_rate(security_currency)
                if rate is not None and rate > 0:
                    price_nok = price_local * rate
        
        if price_nok > 0:
            avg_wac_nok = calculate_consolidated_average_wac(conn, isin)
            fifo_wac_nok = calculate_consolidated_fifo_wac(conn, isin)
            market_value = price_nok * quantity
            avg_cost_basis = avg_wac_nok * quantity
            fifo_cost_basis = fifo_wac_nok * quantity
            
            portfolio_data.append({
                "Symbol": symbol,
                "Quantity": quantity,
                "AvgWAC_NOK": avg_wac_nok,
                "FIFOWAC_NOK": fifo_wac_nok,
                "LatestPrice_NOK": price_nok,
                "MarketValue_NOK": market_value,
                "AvgReturn_pct": (market_value / avg_cost_basis - 1) * 100 if avg_cost_basis > 0 else 0,
                "FIFOReturn_pct": (market_value / fifo_cost_basis - 1) * 100 if fifo_cost_basis > 0 else 0,
                "AvgCostBasis_NOK": avg_cost_basis, # Kept for summary calculation
                "FIFOCostBasis_NOK": fifo_cost_basis, # Kept for summary calculation
            })
        else:
            unpriced_securities.append(f"{symbol} ({isin})")

    if not portfolio_data:
        conn.close()
        return pd.DataFrame(), {}, unpriced_securities

    df = pd.DataFrame(portfolio_data)
    # Filter out "ghost holdings" starting with '0P00'
    df = df[~df['Symbol'].str.startswith('0P00')]
    df = df.sort_values(by="MarketValue_NOK", ascending=False).reset_index(drop=True)
    
    total_market_value = df["MarketValue_NOK"].sum()
    if total_market_value > 0:
        df['Weight'] = df['MarketValue_NOK'] / total_market_value
    else:
        df['Weight'] = 0

    total_avg_cost_basis = df["AvgCostBasis_NOK"].sum()
    total_fifo_cost_basis = df["FIFOCostBasis_NOK"].sum()
    
    c.execute("SELECT Type, SUM(Amount_Base) FROM transactions WHERE Type IN ('FEE', 'DIVIDEND', 'INTEREST') GROUP BY Type")
    other_sums = dict(c.fetchall())
    total_fees = abs(other_sums.get('FEE', 0))
    total_dividends = other_sums.get('DIVIDEND', 0)
    total_interest_paid = abs(other_sums.get('INTEREST', 0))

    cagr_xirr = calculate_xirr(conn, total_market_value, verbose=verbose)
    
    # --- Get last transaction dates by source ---
    c.execute("SELECT Source, MAX(TradeDate) FROM transactions GROUP BY Source ORDER BY Source")
    last_trade_dates_raw = c.fetchall()
    last_trade_dates_formatted = {}
    for source, date_str in last_trade_dates_raw:
        if date_str:
            last_trade_date = parse_date_flexible(date_str)
            if last_trade_date:
                last_trade_dates_formatted[source] = last_trade_date.strftime('%Y-%m-%d')
            else:
                last_trade_dates_formatted[source] = "Invalid Date"
        else:
            last_trade_dates_formatted[source] = "No Transactions"

    summary_data = {
        "total_market_value": total_market_value,
        "total_avg_gain_loss": total_market_value - total_avg_cost_basis,
        "total_avg_return_pct": (total_market_value / total_avg_cost_basis - 1) * 100 if total_avg_cost_basis > 0 else 0,
        "total_fifo_gain_loss": total_market_value - total_fifo_cost_basis,
        "total_fifo_return_pct": (total_market_value / total_fifo_cost_basis - 1) * 100 if total_fifo_cost_basis > 0 else 0,
        "total_fees": total_fees,
        "total_dividends": total_dividends,
        "total_interest_paid": total_interest_paid,
        "cagr_xirr": cagr_xirr,
        "last_trade_dates_by_source": last_trade_dates_formatted # New item
    }
    
    conn.close()
    return df, summary_data, unpriced_securities

if __name__ == '__main__':
    from rich.console import Console
    from rich.table import Table

    console = Console()
    main_df, summary, unpriced = generate_summary_report()

    if not main_df.empty:
        # --- Holdings Table ---
        holdings_table = Table(
            title="Portfolio Holdings",
            show_header=True,
            header_style="bold magenta",
        )
        holdings_table.add_column("Symbol", style="cyan", no_wrap=True)
        holdings_table.add_column("Qty", justify="right")
        holdings_table.add_column("Weight", justify="right")
        holdings_table.add_column("Avg. Cost", justify="right")
        holdings_table.add_column("FIFO Cost", justify="right")
        holdings_table.add_column("Latest Price", justify="right")
        holdings_table.add_column("Market Value", justify="right", style="bold yellow")
        holdings_table.add_column("Return (Avg)", justify="right")
        holdings_table.add_column("Return (FIFO)", justify="right")

        for _, row in main_df.iterrows():
            avg_return_style = "green" if row["AvgReturn_pct"] >= 0 else "red"
            fifo_return_style = "green" if row["FIFOReturn_pct"] >= 0 else "red"
            holdings_table.add_row(
                str(row["Symbol"]),
                f"{row['Quantity']:,.0f}",
                f"{row['Weight']:.2%}",
                f"{row['AvgWAC_NOK']:,.2f}",
                f"{row['FIFOWAC_NOK']:,.2f}",
                f"{row['LatestPrice_NOK']:,.2f}",
                f"{row['MarketValue_NOK']:,.0f}",
                f"[{avg_return_style}]{row['AvgReturn_pct']:.2f}%[/{avg_return_style}]",
                f"[{fifo_return_style}]{row['FIFOReturn_pct']:.2f}%[/{fifo_return_style}]",
            )
        console.print(holdings_table)

        # --- Summary Table ---
        summary_table = Table(
            title="Portfolio Summary",
            show_header=False,
            box=None
        )
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", justify="right")

        summary_table.add_row("Total Market Value", f"{summary['total_market_value']:,.0f}")
        
        avg_gain_style = "green" if summary['total_avg_gain_loss'] >= 0 else "red"
        summary_table.add_row("Total Gain/Loss (Avg)", f"[{avg_gain_style}]{summary['total_avg_gain_loss']:,.0f}[/{avg_gain_style}]")
        avg_return_pct_style = "green" if summary['total_avg_return_pct'] >= 0 else "red"
        summary_table.add_row("Total Return (Avg)", f"[{avg_return_pct_style}]{summary['total_avg_return_pct']:.2f}%[/{avg_return_pct_style}]")

        fifo_gain_style = "green" if summary['total_fifo_gain_loss'] >= 0 else "red"
        summary_table.add_row("Total Gain/Loss (FIFO)", f"[{fifo_gain_style}]{summary['total_fifo_gain_loss']:,.0f}[/{fifo_gain_style}]")
        fifo_return_pct_style = "green" if summary['total_fifo_return_pct'] >= 0 else "red"
        summary_table.add_row("Total Return (FIFO)", f"[{fifo_return_pct_style}]{summary['total_fifo_return_pct']:.2f}%[/{fifo_return_pct_style}]")

        summary_table.add_row("Total Dividends", f"{summary['total_dividends']:,.0f}")
        summary_table.add_row("Total Fees", f"{summary['total_fees']:,.0f}")
        summary_table.add_row("Total Interest Paid", f"{summary['total_interest_paid']:,.0f}")
        summary_table.add_row("CAGR (XIRR)", f"{summary['cagr_xirr']:.2%}")
        
        console.print(summary_table)

        # --- Last Trade Dates by Source ---
        if summary['last_trade_dates_by_source']:
            console.print("\n[bold green]--- Last Transaction Dates by Source ---[/bold green]")
            for source, date_str in summary['last_trade_dates_by_source'].items():
                console.print(f"- [green]{source}[/green]: {date_str}")

        if unpriced:
            console.print("\n[bold yellow]--- Securities Not Priced ---[/bold yellow]")
            for item in unpriced:
                console.print(f"- [yellow]{item}[/yellow]")
    else:
        console.print("[bold red]--- Report Generation Failed: No data ---[/bold red]")
