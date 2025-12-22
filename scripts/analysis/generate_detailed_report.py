import sqlite3
import pandas as pd
from collections import deque
# We will need this for the *current* market value, but not for historical costs
from scripts.pipeline.utils import get_exchange_rate 

# --- WAC Calculation ---

def calculate_average_wac_in_nok(conn, isin, account_id):
    """
    Calculates the Average Weighted Average Cost in NOK for a given ISIN within a specific account,
    using the exchange rate from the transaction data.
    """
    c = conn.cursor()
    c.execute('''
        SELECT Quantity, Price, ExchangeRate, Currency_Local, TradeDate
        FROM transactions
        WHERE ISIN = ? 
        AND AccountID = ?
        AND Type IN ('BUY', 'TRANSFER_IN', 'STOCK_SPLIT') 
        AND Quantity > 0
    ''', (isin, account_id))
    
    transactions = c.fetchall()
    
    total_cost_nok = 0
    total_quantity = 0

    for quantity, price, exchange_rate_str, currency_local, trade_date in transactions:
        cost_nok = 0
        if currency_local == 'NOK':
            cost_nok = quantity * price
        elif exchange_rate_str is not None:
            try:
                exchange_rate = float(str(exchange_rate_str).replace(',', '.'))
                if exchange_rate != 0:
                    cost_nok = quantity * price * exchange_rate
            except (ValueError, AttributeError):
                 print(f"Warning: Could not parse exchange rate '{exchange_rate_str}' for a transaction in {isin} on {trade_date}. Cost will be 0.")
        else:
            # This case should no longer happen if the enrichment script has been run.
            print(f"Warning: Exchange rate is missing for a foreign currency transaction in {isin} on {trade_date}. Cost will be 0.")

        total_cost_nok += cost_nok
        total_quantity += quantity

    if total_quantity > 0:
        return total_cost_nok / total_quantity
    return 0

def calculate_fifo_wac_in_nok(conn, isin, account_id):
    """
    Calculates the FIFO Weighted Average Cost in NOK for a given ISIN within a specific account.
    """
    c = conn.cursor()
    # Fetch all relevant transactions, ordered by date
    c.execute('''
        SELECT Quantity, Price, ExchangeRate, Currency_Local, Type, TradeDate
        FROM transactions
        WHERE ISIN = ? 
        AND AccountID = ?
        AND Type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT', 'STOCK_SPLIT')
        ORDER BY TradeDate, GlobalID
    ''', (isin, account_id))
    
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
                    print(f"Warning: Could not parse exchange rate '{exchange_rate_str}' for a transaction in {isin} on {trade_date}. Cost will be 0.")
            else:
                # This case should no longer happen if the enrichment script has been run.
                print(f"Warning: Exchange rate is missing for a foreign currency transaction in {isin} on {trade_date}. Cost will be 0.")
            
            buy_lots.append({'quantity': quantity, 'cost_nok': cost_nok})

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
        total_cost_nok += lot['cost_nok']
        total_quantity += lot['quantity']

    if total_quantity > 0:
        return total_cost_nok / total_quantity
    return 0


# --- Main Report Generation ---

def generate_portfolio_report():
    """
    Generates and prints a detailed portfolio report on the fly, with all values in NOK.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Get current holdings
    c.execute('''
        SELECT AccountID, ISIN, SUM(Quantity) as Quantity
        FROM transactions
        WHERE ISIN IS NOT NULL
        GROUP BY AccountID, ISIN
        HAVING SUM(Quantity) > 0
    ''')
    holdings = c.fetchall()

    portfolio_data = []
    unpriced_securities = []
    
    for account_id, isin, quantity in holdings:
        # Get symbol and currency
        c.execute('SELECT Symbol, Currency FROM isin_symbol_map WHERE ISIN = ?', (isin,))
        mapping_result = c.fetchone()
        symbol = mapping_result[0] if mapping_result else 'N/A'
        security_currency = mapping_result[1] if mapping_result else None

        # Calculate WACs
        avg_wac_nok = calculate_average_wac_in_nok(conn, isin, account_id)
        fifo_wac_nok = calculate_fifo_wac_in_nok(conn, isin, account_id)

        # Get current price
        c.execute('SELECT Price FROM current_prices WHERE ISIN = ?', (isin,))
        price_result = c.fetchone()
        price_local = price_result[0] if price_result else 0
        
        price_nok = 0
        if price_local > 0 and security_currency:
            latest_rate = get_exchange_rate(security_currency) # Use the new function
            if latest_rate:
                price_nok = price_local * latest_rate
        
        if price_nok == 0:
            unpriced_securities.append(f"{symbol} ({isin}) in account {account_id}")

        # Calculations for Average Cost method
        avg_cost_basis_nok = avg_wac_nok * quantity
        avg_gain_loss_nok = price_nok * quantity - avg_cost_basis_nok
        avg_return_pct = (avg_gain_loss_nok / avg_cost_basis_nok) * 100 if avg_cost_basis_nok > 0 else 0

        # Calculations for FIFO method
        fifo_cost_basis_nok = fifo_wac_nok * quantity
        fifo_gain_loss_nok = price_nok * quantity - fifo_cost_basis_nok
        fifo_return_pct = (fifo_gain_loss_nok / fifo_cost_basis_nok) * 100 if fifo_cost_basis_nok > 0 else 0

        portfolio_data.append({
            "AccountID": account_id,
            "Symbol": symbol,
            "Quantity": quantity,
            "AvgWAC_NOK": avg_wac_nok,
            "AvgCostBasis_NOK": avg_cost_basis_nok,
            "FIFO_WAC_NOK": fifo_wac_nok,
            "FIFOCostBasis_NOK": fifo_cost_basis_nok,
            "CurrentPrice_NOK": price_nok,
            "MarketValue_NOK": price_nok * quantity,
            "FIFO_GainLoss_NOK": fifo_gain_loss_nok,
            "FIFO_Return": fifo_return_pct,
            "Avg_Return": avg_return_pct,
        })

    if not portfolio_data:
        print("No portfolio data to display.")
        return

    # Create DataFrame and print summary
    df = pd.DataFrame(portfolio_data)
    
    # Filter out "dust" holdings (e.g. < 0.001) resulting from rounding errors or fractional remainders
    df = df[df['Quantity'] >= 0.001].copy()

    # Calculate returns
    df['Avg_Return'] = df.apply(lambda row: (row['MarketValue_NOK'] - row['AvgCostBasis_NOK']) / row['AvgCostBasis_NOK'] * 100 if row['AvgCostBasis_NOK'] > 0 else 0, axis=1)
    
    print("\n--- Portfolio Overview (all values in NOK) ---")
    
    display_cols = ["Symbol", "Quantity", "AvgWAC_NOK", "FIFO_WAC_NOK", "MarketValue_NOK", "Avg_Return", "FIFO_Return"]

    for account in sorted(df['AccountID'].unique()):
        account_df = df[df['AccountID'] == account].copy()
        
        # Format the numbers
        for col in ["AvgWAC_NOK", "FIFO_WAC_NOK", "MarketValue_NOK"]:
             account_df[col] = account_df[col].map('{:,.2f}'.format)
        account_df['Avg_Return'] = account_df['Avg_Return'].map('{:.2f}%'.format)
        account_df['FIFO_Return'] = account_df['FIFO_Return'].map('{:.2f}%'.format)

        print(f"\n--- Account: {account} ---")
        print(account_df[display_cols].to_string(index=False))
        
        account_avg_cost_basis = df[df['AccountID'] == account]["AvgCostBasis_NOK"].sum()
        account_fifo_cost_basis = df[df['AccountID'] == account]["FIFOCostBasis_NOK"].sum()
        account_market_value = df[df['AccountID'] == account]["MarketValue_NOK"].sum()
        
        account_avg_gain_loss = account_market_value - account_avg_cost_basis
        account_avg_return_pct = (account_avg_gain_loss / account_avg_cost_basis) * 100 if account_avg_cost_basis > 0 else 0
        
        account_fifo_gain_loss = account_market_value - account_fifo_cost_basis
        account_fifo_return_pct = (account_fifo_gain_loss / account_fifo_cost_basis) * 100 if account_fifo_cost_basis > 0 else 0
        
        print(f"\n  Account Market Value: {account_market_value:,.2f} NOK")
        print(f"  Account Avg Return: {account_avg_return_pct:.2f}%")
        print(f"  Account FIFO Return: {account_fifo_return_pct:.2f}%")
    
    # Grand Totals
    total_avg_cost_basis = df["AvgCostBasis_NOK"].sum()
    total_fifo_cost_basis = df["FIFOCostBasis_NOK"].sum()
    total_market_value = df["MarketValue_NOK"].sum()

    # Last Transaction Dates by Source
    c.execute("SELECT Source, MAX(TradeDate) FROM transactions GROUP BY Source ORDER BY Source")
    last_trade_dates = c.fetchall()

    conn.close()

    total_avg_gain_loss = total_market_value - total_avg_cost_basis
    total_avg_return_pct = (total_avg_gain_loss / total_avg_cost_basis) * 100 if total_avg_cost_basis > 0 else 0
    
    total_fifo_gain_loss = total_market_value - total_fifo_cost_basis
    total_fifo_return_pct = (total_fifo_gain_loss / total_fifo_cost_basis) * 100 if total_fifo_cost_basis > 0 else 0

    print("\n\n--- Total Portfolio Summary (in NOK) ---")
    print(f"Total Market Value: {total_market_value:,.2f} NOK")
    print(f"Total Avg Cost Return: {total_avg_return_pct:.2f}%")
    print(f"Total FIFO Return: {total_fifo_return_pct:.2f}%")

    # Last Transaction Dates by Source
    print("\n--- Last Transaction Dates by Source ---")
    for source, date_str in last_trade_dates:
        if date_str:
             # Just show the date part
             print(f"- {source}: {date_str[:10]}")
        else:
             print(f"- {source}: No Transactions")

    if unpriced_securities:
        print("\n\n--- Securities Without a Current Price ---")
        for item in unpriced_securities:
            print(f"- {item}")

if __name__ == '__main__':
    generate_portfolio_report()
