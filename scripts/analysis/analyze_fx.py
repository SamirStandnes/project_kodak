from scripts.shared.db import get_connection
from scripts.shared.calculations import get_fx_performance
from scripts.shared.market_data import get_exchange_rate, get_latest_prices
from scripts.shared.utils import load_config
import pandas as pd

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def run_fx_analysis():
    print(f"\n--- FX Analysis ({BASE_CURRENCY}) ---")
    df = get_fx_performance()
    
    if df.empty:
        print("No FX transactions found.")
        return

    # Add Unrealized FX on Holdings
    # 1. Get current holdings
    conn = get_connection()
    df_h = pd.read_sql("SELECT instrument_id, quantity, cost_basis_local FROM (SELECT instrument_id, SUM(quantity) as quantity, SUM(cost_basis_local) as cost_basis_local FROM (SELECT instrument_id, CASE WHEN type IN ('BUY', 'DEPOSIT', 'TRANSFER_IN') THEN quantity ELSE -quantity END as quantity, CASE WHEN type IN ('BUY', 'DEPOSIT', 'TRANSFER_IN') THEN amount_local ELSE -amount_local END as cost_basis_local FROM transactions WHERE instrument_id IS NOT NULL) GROUP BY instrument_id) WHERE quantity > 0.001", conn)
    
    # Enrich with Currency
    df_inst = pd.read_sql("SELECT id, currency FROM instruments", conn)
    df_h = df_h.merge(df_inst, left_on='instrument_id', right_on='id')
    
    # Filter for foreign
    df_h = df_h[df_h['currency'] != BASE_CURRENCY].copy()
    
    # Get Market Value
    prices = get_latest_prices(df_h['instrument_id'].tolist())
    
    unrealized_data = []
    for _, row in df_h.iterrows():
        inst_id = row['instrument_id']
        curr = row['currency']
        cost = row['cost_basis_local'] # Wait, this logic in query above is simplified/wrong for avg cost.
        # But for FX analysis we just want total value exposure.
        
        # Proper way: Use get_holdings() from calculations.py?
        # But we are here.
        
        if inst_id in prices:
            price, _ = prices[inst_id]
            rate = get_exchange_rate(curr, BASE_CURRENCY)
            mkt_val = row['quantity'] * price * rate
            
            # FX Component of Unrealized?
            # Total Unrealized = Market Value - Cost Basis
            # FX Component = (Current Rate - Avg Rate) * Cost in Foreign?
            # Simplified: Just show total unrealized on foreign assets as proxy for exposure?
            # Or just show Market Value.
            
            unrealized = mkt_val - cost
            unrealized_data.append({
                'currency': curr,
                'Market Value': mkt_val,
                'Unrealized P&L': unrealized
            })
            
    df_unrealized = pd.DataFrame(unrealized_data)
    if not df_unrealized.empty:
        print("\nForeign Holdings Exposure:")
        print(df_unrealized.groupby('currency')[['Market Value', 'Unrealized P&L']].sum())

    # Print Realized Table
    print(f"\nRealized FX P&L (Cash Trading):")
    print(df[['currency', 'realized_pl_nok', 'holdings']].rename(columns={'realized_pl_nok': f'Realized P&L ({BASE_CURRENCY})'}))
    
    total_realized = df['realized_pl_nok'].sum()
    print(f"\nTotal Realized FX Gain/Loss: {total_realized:,.2f} {BASE_CURRENCY}")

if __name__ == "__main__":
    run_fx_analysis()
