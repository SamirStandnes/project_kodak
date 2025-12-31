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
    
    # 3. Largest Payments
    df_top = pd.read_sql_query("""
        SELECT 
            date, 
            currency, 
            ABS(amount) as amount, 
            ABS(amount_local) as amount_local,
            source_file
        FROM transactions
        WHERE type = 'INTEREST'
        ORDER BY amount_local DESC
        LIMIT 20
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

    # 3. Largest Fees
    df_top = pd.read_sql_query("""
        SELECT 
            date, 
            currency, 
            CASE 
                WHEN type = 'FEE' THEN ABS(amount_local) 
                ELSE fee_local 
            END as amount_local,
            source_file,
            notes as description
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        ORDER BY amount_local DESC
        LIMIT 20
    """, conn)
    
    conn.close()
    return df_yearly, df_currency, df_top

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
