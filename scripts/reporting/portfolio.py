import pandas as pd
import numpy as np
from scripts.shared.db import get_connection

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
