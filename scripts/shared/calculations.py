import pandas as pd
import numpy as np
from scripts.shared.db import get_connection, execute_query

def get_income_and_costs():
    """
    Returns the total Dividends, Interest (absolute), and Fees (absolute).
    """
    row = execute_query('''
        SELECT 
            SUM(CASE WHEN type = 'DIVIDEND' THEN amount_local ELSE 0 END) as dividends,
            SUM(CASE WHEN type = 'INTEREST' THEN ABS(amount_local) ELSE 0 END) as interest,
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as fees
        FROM transactions
    ''')[0]
    
    return {
        'dividends': row['dividends'] or 0,
        'interest': row['interest'] or 0,
        'fees': row['fees'] or 0
    }

def get_dividend_details():
    """
    Returns detailed dividend data:
    1. Yearly totals
    2. Top payers (Current Year - 2025)
    3. Top payers (All Time)
    """
    conn = get_connection()
    
    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            SUM(amount_local) as total
        FROM transactions
        WHERE type = 'DIVIDEND'
        GROUP BY year
        ORDER BY year
    """, conn)
    
    # 2. By Ticker (2025)
    df_current_year = pd.read_sql_query("""
        SELECT 
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND' AND t.date LIKE '2025%'
        GROUP BY symbol
        ORDER BY total DESC
    """, conn)
    
    # 3. By Ticker (All Time)
    df_all_time = pd.read_sql_query("""
        SELECT 
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND'
        GROUP BY symbol
        ORDER BY total DESC
    """, conn)
    
    conn.close()
    return df_yearly, df_current_year, df_all_time

def get_interest_details():
    """
    Returns detailed interest data:
    1. Yearly totals
    2. By Currency
    3. Top Payments
    """
    conn = get_connection()
    
    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            SUM(ABS(amount_local)) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY year
        ORDER BY year
    """, conn)
    
    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT 
            currency, 
            SUM(ABS(amount_local)) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY currency
        ORDER BY total DESC
    """, conn)
    
    # 3. Recent Payments
    df_top = pd.read_sql_query("""
        SELECT 
            date, 
            currency, 
            ABS(amount) as amount, 
            ABS(amount_local) as amount_local,
            source_file
        FROM transactions
        WHERE type = 'INTEREST'
        ORDER BY date DESC
        LIMIT 50
    """, conn)
    
    conn.close()
    return df_yearly, df_currency, df_top

def get_fee_details():
    """
    Returns detailed fee data:
    1. Yearly totals
    2. By Currency
    3. Top Payments
    """
    conn = get_connection()
    
    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY year
        ORDER BY year
    """, conn)
    
    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT 
            currency, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY currency
        ORDER BY total DESC
    """, conn)

    # 3. Recent Fees
    df_top = pd.read_sql_query("""
        SELECT 
            date, 
            currency, 
            CASE 
                WHEN type = 'FEE' THEN ABS(amount_local) 
                ELSE fee_local 
            END as amount_local,
            source_file
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        ORDER BY date DESC
        LIMIT 50
    """, conn)
    
    conn.close()
    return df_yearly, df_currency, df_top

def get_realized_performance():
    """
    Replays the ledger to calculate Realized Gains, Dividends, Fees, etc. by Year.
    Returns a DataFrame: year | realized_gl | dividends | interest | fees | tax | total_pl
    """
    conn = get_connection()
    
    # Get all transactions sorted by date
    query = '''
        SELECT 
            t.date, t.type, t.instrument_id, t.quantity, t.amount_local, 
            t.fee_local, i.symbol
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        ORDER BY t.date, t.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()

    # State
    holdings = {} # inst_id -> {qty, total_cost}
    yearly = {}   # year -> {realized, div, int, fee, tax}

    def get_year(date_str):
        return str(date_str)[:4]

    def add_stat(year, category, value):
        if year not in yearly:
            yearly[year] = {'realized_gl': 0.0, 'dividends': 0.0, 'interest': 0.0, 'fees': 0.0, 'tax': 0.0}
        yearly[year][category] += value

    # Replay
    for _, row in df.iterrows():
        year = get_year(row['date'])
        t_type = row['type']
        inst_id = row['instrument_id']
        qty = row['quantity']
        amt = row['amount_local']
        fee = row['fee_local'] if pd.notna(row['fee_local']) else 0.0
        
        # Always track fees
        if fee > 0:
            add_stat(year, 'fees', -abs(fee)) # fees are negative impact
        
        # 1. Income / Costs
        if t_type == 'DIVIDEND':
            add_stat(year, 'dividends', amt)
        elif t_type == 'INTEREST':
            add_stat(year, 'interest', amt) # usually negative
        elif t_type == 'TAX':
            add_stat(year, 'tax', amt)      # usually negative
        elif t_type == 'FEE':
            add_stat(year, 'fees', -abs(amt)) # Explicit fee transaction

        # 2. Capital Gains (Buy/Sell)
        # Only process if instrument is involved
        if inst_id:
            if inst_id not in holdings:
                holdings[inst_id] = {'qty': 0.0, 'cost': 0.0}
            
            h = holdings[inst_id]
            
            # Identify Buy vs Sell using logic similar to get_holdings
            # We assume 'amount' sign tells us flow, but we need to be careful with cost basis logic.
            
            # INFLOW (Buy)
            if t_type in ['BUY', 'DEPOSIT', 'TRANSFER_IN', 'TILDELING INNLEGG RE']:
                # Add to inventory
                h['qty'] += qty
                # Cost increases by amount paid (usually negative amount, so we take abs)
                # But transfer_in might have positive qty and 0 amount? 
                # Ideally we need cost basis for transfers. Assuming 0 or amount_local if set.
                cost_added = abs(amt) 
                h['cost'] += cost_added
                
            # OUTFLOW (Sell)
            elif t_type in ['SELL', 'WITHDRAWAL', 'TRANSFER_OUT', 'INNLØSN. UTTAK VP']:
                # Calculate Realized Gain
                # Avg Cost Basis
                if h['qty'] > 0:
                    avg_cost = h['cost'] / h['qty']
                    cost_of_sold = avg_cost * abs(qty)
                    
                    # Proceeds = Amount received (positive for sell)
                    proceeds = abs(amt)
                    
                    # Gain = Proceeds - Cost
                    # Note: For withdrawals/transfers, proceeds might be 0, implying a "loss" or just moving assets?
                    # Usually checking Realized Gain only makes sense for SELL or INNLØSN.
                    if t_type in ['SELL', 'INNLØSN. UTTAK VP']:
                        gain = proceeds - cost_of_sold
                        add_stat(year, 'realized_gl', gain)
                    
                    # Reduce Inventory
                    h['cost'] -= cost_of_sold
                
                h['qty'] += qty # qty is negative
                
                # Cleanup dust
                if abs(h['qty']) < 0.001:
                    h['qty'] = 0.0
                    h['cost'] = 0.0

    # Convert to DataFrame
    data = []
    for year, stats in yearly.items():
        row = stats.copy()
        row['year'] = year
        row['total_pl'] = sum(stats.values())
        data.append(row)
        
    return pd.DataFrame(data).sort_values('year')

def get_fx_performance():
    """
    Calculates Realized P&L, Remaining Holdings, and Cost Basis for FX trades.
    Returns a DataFrame.
    """
    conn = get_connection()
    
    # Fetch all FX transactions for non-NOK currencies
    query = """
        SELECT 
            date,
            currency,
            amount as quantity,
            amount_local
        FROM transactions
        WHERE type = 'CURRENCY_EXCHANGE' 
          AND currency != 'NOK'
        ORDER BY date, id
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()

    results = []
    
    # Process each currency
    for currency, group in df.groupby('currency'):
        holdings = 0.0
        total_cost = 0.0
        realized_pl = 0.0
        
        # Sort just in case
        group = group.sort_values('date')
        
        for _, row in group.iterrows():
            qty = row['quantity']
            val_nok = row['amount_local']
            
            if qty > 0:
                # BUY (Inflow of Foreign Currency)
                holdings += qty
                total_cost += val_nok
                
            elif qty < 0:
                # SELL (Outflow of Foreign Currency)
                if holdings <= 0:
                    cost_portion = 0
                else:
                    portion = abs(qty) / holdings
                    portion = min(portion, 1.0)
                    cost_portion = total_cost * portion
                
                proceeds = abs(val_nok)
                gain = proceeds - cost_portion
                realized_pl += gain
                
                # Update Inventory
                holdings += qty 
                total_cost -= cost_portion
                
                if abs(holdings) < 0.01:
                    holdings = 0
                    total_cost = 0
        
        results.append({
            'currency': currency,
            'realized_pl_nok': realized_pl,
            'holdings': holdings,
            'cost_basis_nok': total_cost
        })
        
    return pd.DataFrame(results)

def get_holdings(date=None):
    """
    Calculates current holdings and average cost basis.
    Handles various transaction types to ensure quantity nets to zero for closed positions.
    """
    conn = get_connection()
    
    date_filter = ""
    params = []
    if date:
        date_filter = "AND t.date <= ?"
        params = [date]

    query = f'''
        SELECT 
            t.instrument_id,
            t.type,
            t.quantity,
            t.amount_local,
            t.date,
            i.symbol,
            i.isin
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.instrument_id IS NOT NULL {date_filter}
        ORDER BY t.instrument_id, t.date
    '''
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()

    # Classification
    # Positive movements (Add to total_qty)
    INFLOW_TYPES = ['BUY', 'DEPOSIT', 'TILDELING INNLEGG RE', 'BYTTE INNLEGG VP', 'TRANSFER_IN', 'EMISJON INNLEGG VP']
    # Negative movements (Subtract from total_qty)
    OUTFLOW_TYPES = ['SELL', 'WITHDRAWAL', 'BYTTE UTTAK VP', 'TRANSFER_OUT', 'INNLØSN. UTTAK VP']

    final_holdings = []
    
    for inst_id, group in df.groupby('instrument_id'):
        total_qty = 0.0
        total_cost = 0.0
        
        first_row = group.iloc[0]
        
        for _, row in group.iterrows():
            t_type = row['type']
            qty = row['quantity']
            amt = abs(row['amount_local'])
            
            # Use starts-with/contains for more robustness
            is_inflow = any(t in t_type for t in INFLOW_TYPES)
            is_outflow = any(t in t_type for t in OUTFLOW_TYPES)
            
            if is_inflow:
                total_qty += qty
                total_cost += amt
                
            elif is_outflow:
                if total_qty > 0:
                    # Remove proportional cost
                    avg_cost_per_share = total_cost / total_qty
                    # qty is already negative from parser for outflows
                    cost_removed = avg_cost_per_share * abs(qty)
                    total_cost -= cost_removed
                    
                total_qty += qty # adds negative qty
            
            # Note: For types like DIVIDEND, INTEREST, FEE, TAX etc., 
            # they don't affect quantity or cost basis in a simple WAC model.
            
        # Filter dust
        if abs(total_qty) > 0.001:
            final_holdings.append({
                'instrument_id': inst_id,
                'symbol': first_row['symbol'],
                'isin': first_row['isin'],
                'quantity': total_qty,
                'cost_basis_local': max(0, total_cost)
            })
            
    return pd.DataFrame(final_holdings)
