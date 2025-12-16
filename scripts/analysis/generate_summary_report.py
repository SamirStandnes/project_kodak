import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from collections import deque
import pyxirr

# --- Exchange Rate Functions ---

# Cache for latest exchange rates to avoid re-fetching
latest_rates_cache = {}

def get_latest_exchange_rate(base_currency, target_currency='NOK'):
    """
    Gets the latest exchange rate between two currencies.
    """
    if base_currency == target_currency:
        return 1.0
    
    # Special handling for HKD
    if base_currency == 'HKD' and target_currency == 'NOK':
        usd_nok_rate = get_latest_exchange_rate('USD', 'NOK')
        hkd_usd_rate = get_latest_exchange_rate('HKD', 'USD')
        if usd_nok_rate and hkd_usd_rate:
            return usd_nok_rate * hkd_usd_rate
        else:
            return None

    ticker = f"{base_currency}{target_currency}=X"
    if ticker in latest_rates_cache:
        return latest_rates_cache[ticker]

    try:
        rate_data = yf.Ticker(ticker).history(period="1d")
        if not rate_data.empty:
            rate = rate_data['Close'].iloc[0]
            latest_rates_cache[ticker] = rate
            return rate
        else:
            print(f"Warning: Could not fetch latest exchange rate for {ticker}")
            return None
    except Exception as e:
        print(f"Warning: Error fetching latest rate for {ticker}: {e}")
        return None

# --- WAC & XIRR Calculation Functions ---

def calculate_consolidated_average_wac(conn, isin):
    """
    Calculates the Average WAC in NOK for a given ISIN across all accounts.
    """
    c = conn.cursor()
    c.execute('''
        SELECT Quantity, Price, ExchangeRate, Currency_Local
        FROM transactions
        WHERE ISIN = ? AND Type IN ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT') AND Quantity > 0
    ''', (isin,))
    
    transactions = c.fetchall()
    
    total_cost_nok = 0
    total_quantity = 0

    for quantity, price, exchange_rate_str, currency_local in transactions:
        cost_nok = 0
        if currency_local == 'NOK':
            cost_nok = quantity * price
        elif exchange_rate_str is not None:
            try:
                exchange_rate = float(str(exchange_rate_str).replace(',', '.'))
                if exchange_rate != 0:
                    cost_nok = quantity * price * exchange_rate
            except (ValueError, AttributeError):
                pass 

        total_cost_nok += cost_nok
        total_quantity += quantity

    if total_quantity > 0:
        return total_cost_nok / total_quantity
    return 0

def calculate_consolidated_fifo_wac(conn, isin):
    """
    Calculates the FIFO WAC in NOK for a given ISIN across all accounts.
    """
    c = conn.cursor()
    # Fetch all relevant transactions, ordered by date
    c.execute('''
        SELECT Quantity, Price, ExchangeRate, Currency_Local, Type, TradeDate
        FROM transactions
        WHERE ISIN = ? AND Type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT', 'STOCK_SPLIT')
        ORDER BY TradeDate, GlobalID
    ''', (isin,))
    
    transactions = c.fetchall()
    
    buy_lots = deque() # Use a deque to efficiently remove from the front (FIFO)

    for quantity, price, exchange_rate_str, currency_local, trans_type, trade_date in transactions:
        
        if trans_type in ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT'):
            cost_nok = 0
            if currency_local == 'NOK':
                cost_nok = quantity * price
            elif exchange_rate_str is not None:
                try:
                    exchange_rate = float(str(exchange_rate_str).replace(',', '.'))
                    if exchange_rate != 0:
                        cost_nok = quantity * price * exchange_rate
                except (ValueError, AttributeError):
                    pass # Keep cost_nok as 0 if rate is invalid
            
            buy_lots.append({'quantity': quantity, 'cost_per_share_nok': cost_nok / quantity if quantity > 0 else 0})

        elif trans_type in ('SELL', 'TRANSFER_OUT'):
            sell_quantity = abs(quantity)
            
            while sell_quantity > 0 and buy_lots:
                oldest_lot = buy_lots[0]
                
                if oldest_lot['quantity'] <= sell_quantity:
                    # This lot is completely sold
                    sell_quantity -= oldest_lot['quantity']
                    buy_lots.popleft()
                else:
                    # This lot is partially sold
                    oldest_lot['quantity'] -= sell_quantity
                    sell_quantity = 0

    # Calculate WAC from the remaining lots
    total_cost_nok = 0
    total_quantity = 0
    for lot in buy_lots:
        total_cost_nok += lot['quantity'] * lot['cost_per_share_nok']
        total_quantity += lot['quantity']

    if total_quantity > 0:
        return total_cost_nok / total_quantity
    return 0

def calculate_xirr(conn, total_market_value):
    """
    Calculates the XIRR (annualized return) of the entire portfolio.
    """
    c = conn.cursor()
    # Get all cashflow-related transactions
    c.execute('''
        SELECT TradeDate, Type, Amount_Base
        FROM transactions
        WHERE Type IN ('DEPOSIT', 'WITHDRAWAL', 'BUY', 'SELL', 'FEE', 'DIVIDEND')
    ''')
    
    transactions = c.fetchall()
    
    dates = []
    values = []

    for trade_date, trans_type, amount_base in transactions:
        if amount_base is not None:
            dates.append(pd.to_datetime(trade_date).date())
            if trans_type in ('WITHDRAWAL', 'FEE') and amount_base > 0:
                values.append(-amount_base)
            else:
                values.append(amount_base)

    # Add the current market value as the final cashflow
    dates.append(datetime.today().date())
    values.append(total_market_value)
    
    valid_dates = []
    valid_values = []
    for d, v in zip(dates, values):
        if pd.notna(d) and pd.notna(v):
            valid_dates.append(d)
            valid_values.append(v)

    if len(valid_dates) < 2:
        return 0

    try:
        return pyxirr.xirr(valid_dates, valid_values)
    except Exception as e:
        print(f"\nCould not calculate Annualized Return (XIRR): {e}")
        return 0

# --- Main Report Generation ---

def generate_summary_report(verbose=True):
    """
    Generates consolidated portfolio data.
    If verbose is True, it prints status messages to the console during execution.
    Returns a tuple containing:
    - A pandas DataFrame with detailed position data.
    - A dictionary with summary portfolio metrics.
    - A list of securities for which no current price was found.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Get current consolidated holdings
    c.execute('''
        SELECT ISIN, SUM(Quantity) as Quantity
        FROM transactions
        WHERE ISIN IS NOT NULL
        GROUP BY ISIN
        HAVING SUM(Quantity) > 0
    ''')
    holdings = c.fetchall()

    portfolio_data = []
    unpriced_securities = []

    # Pre-fetch latest exchange rates
    all_currencies = pd.read_sql_query("SELECT DISTINCT Currency FROM isin_symbol_map", conn)['Currency'].tolist()
    if verbose:
        print("Fetching latest exchange rates...")
    for currency in all_currencies:
        if currency:
            get_latest_exchange_rate(currency)
    if verbose:
        print("Exchange rate fetching complete.")

    for isin, quantity in holdings:
        c.execute('SELECT Symbol, Currency FROM isin_symbol_map WHERE ISIN = ?', (isin,))
        mapping_result = c.fetchone()
        symbol = mapping_result[0] if mapping_result else 'N/A'
        security_currency = mapping_result[1] if mapping_result else None

        avg_wac_nok = calculate_consolidated_average_wac(conn, isin)
        fifo_wac_nok = calculate_consolidated_fifo_wac(conn, isin)

        c.execute('SELECT Price FROM current_prices WHERE ISIN = ?', (isin,))
        price_result = c.fetchone()
        price_local = price_result[0] if price_result else 0
        
        price_nok = 0
        if price_local > 0 and security_currency:
            latest_rate = get_latest_exchange_rate(security_currency)
            if latest_rate:
                price_nok = price_local * latest_rate
        
        if price_nok == 0:
            unpriced_securities.append(f"{symbol} ({isin})")

        avg_cost_basis = avg_wac_nok * quantity
        fifo_cost_basis = fifo_wac_nok * quantity
        market_value = price_nok * quantity
        
        avg_gain_loss = market_value - avg_cost_basis
        avg_return_pct = (avg_gain_loss / avg_cost_basis) * 100 if avg_cost_basis > 0 else 0
        
        fifo_gain_loss = market_value - fifo_cost_basis
        fifo_return_pct = (fifo_gain_loss / fifo_cost_basis) * 100 if fifo_cost_basis > 0 else 0

        portfolio_data.append({
            "Symbol": symbol,
            "Quantity": quantity,
            "AvgWAC_NOK": avg_wac_nok,
            "FIFOWAC_NOK": fifo_wac_nok,
            "MarketValue_NOK": market_value,
            "AvgReturn_pct": avg_return_pct,
            "FIFOReturn_pct": fifo_return_pct,
            "AvgCostBasis_NOK": avg_cost_basis,
            "FIFOCostBasis_NOK": fifo_cost_basis,
        })

    c.execute("SELECT SUM(Amount_Base) FROM transactions WHERE Type = 'FEE'")
    total_fees_result = c.fetchone()
    total_fees = abs(total_fees_result[0]) if total_fees_result and total_fees_result[0] is not None else 0

    c.execute("SELECT SUM(Amount_Base) FROM transactions WHERE Type = 'DIVIDEND'")
    total_dividends_result = c.fetchone()
    total_dividends = total_dividends_result[0] if total_dividends_result and total_dividends_result[0] is not None else 0

    c.execute("SELECT SUM(Amount_Base) FROM transactions WHERE Type = 'INTEREST'")
    total_interest_result = c.fetchone()
    total_interest_paid = abs(total_interest_result[0]) if total_interest_result and total_interest_result[0] is not None else 0
    
    conn.close()

    if not portfolio_data:
        return pd.DataFrame(), {}, []

    df = pd.DataFrame(portfolio_data)
    df = df.sort_values(by="MarketValue_NOK", ascending=False).reset_index(drop=True)
    df = df[df["MarketValue_NOK"] > 0]
    
    total_market_value = df["MarketValue_NOK"].sum()
    
    total_avg_cost_basis = df["AvgCostBasis_NOK"].sum()
    total_avg_gain_loss = total_market_value - total_avg_cost_basis
    total_avg_return_pct = (total_avg_gain_loss / total_avg_cost_basis) * 100 if total_avg_cost_basis > 0 else 0

    total_fifo_cost_basis = df["FIFOCostBasis_NOK"].sum()
    total_fifo_gain_loss = total_market_value - total_fifo_cost_basis
    total_fifo_return_pct = (total_fifo_gain_loss / total_fifo_cost_basis) * 100 if total_fifo_cost_basis > 0 else 0

    summary_data = {
        "total_market_value": total_market_value,
        "total_avg_cost_basis": total_avg_cost_basis,
        "total_avg_gain_loss": total_avg_gain_loss,
        "total_avg_return_pct": total_avg_return_pct,
        "total_fifo_cost_basis": total_fifo_cost_basis,
        "total_fifo_gain_loss": total_fifo_gain_loss,
        "total_fifo_return_pct": total_fifo_return_pct,
        "total_fees": total_fees,
        "total_dividends": total_dividends,
        "total_interest_paid": total_interest_paid,
    }
            
    return df, summary_data, unpriced_securities

if __name__ == '__main__':
    # This block allows the script to be run directly and still produce the original text report.
    main_df, summary, unpriced = generate_summary_report()

    if main_df.empty:
        print("No portfolio data to display.")
    else:
        report_lines = []
        report_lines.append("--- Consolidated Portfolio Positions (all values in NOK) ---")
        
        # Create a display-friendly version of the DataFrame
        df_display = main_df.copy()
        df_display['Quantity'] = df_display['Quantity'].map('{:,.0f}'.format)
        for col in ["AvgWAC_NOK", "FIFOWAC_NOK", "MarketValue_NOK"]:
            df_display[col] = df_display[col].map('{:,.0f}'.format)
        df_display['AvgReturn_pct'] = df_display['AvgReturn_pct'].map('{:.2f}%'.format)
        df_display['FIFOReturn_pct'] = df_display['FIFOReturn_pct'].map('{:.2f}%'.format)
        
        display_cols = ["Symbol", "Quantity", "AvgWAC_NOK", "FIFOWAC_NOK", "MarketValue_NOK", "AvgReturn_pct", "FIFOReturn_pct"]
        # Rename columns for display
        df_display.rename(columns={"AvgReturn_pct": "AvgReturn", "FIFOReturn_pct": "FIFOReturn"}, inplace=True)

        report_lines.append(df_display[display_cols].to_string(index=False))
        
        report_lines.append("\n\n--- Portfolio Summary (in NOK) ---")
        report_lines.append(f"Total Market Value: {summary['total_market_value']:,.0f} NOK")
        report_lines.append("\n--- Based on Average Cost ---")
        report_lines.append(f"  Cost Basis: {summary['total_avg_cost_basis']:,.0f} NOK")
        report_lines.append(f"  Gain/Loss: {summary['total_avg_gain_loss']:,.0f} NOK")
        report_lines.append(f"  Return: {summary['total_avg_return_pct']:.2f}%")
        
        report_lines.append("\n--- Based on FIFO (Broker/Tax) ---")
        report_lines.append(f"  Cost Basis: {summary['total_fifo_cost_basis']:,.0f} NOK")
        report_lines.append(f"  Gain/Loss: {summary['total_fifo_gain_loss']:,.0f} NOK")
        report_lines.append(f"  Return: {summary['total_fifo_return_pct']:.2f}%")

        report_lines.append("\n--- Other Information ---")
        report_lines.append(f"Total Fees Paid: {summary['total_fees']:,.0f} NOK")
        report_lines.append(f"Total Dividends: {summary['total_dividends']:,.0f} NOK")
        report_lines.append(f"Total Interest Paid: {summary['total_interest_paid']:,.0f} NOK")

        if unpriced:
            report_lines.append("\n\n--- Securities Without a Current Price ---")
            for item in unpriced:
                report_lines.append(f"- {item}")
        
        print("\n".join(report_lines))
