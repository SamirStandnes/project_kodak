import pandas as pd
from scripts.shared.calculations import get_fx_performance
from scripts.shared.market_data import get_exchange_rate

def analyze_fx():
    print("Analyzing FX Performance...")
    df = get_fx_performance()
    
    if df.empty:
        print("No currency exchange transactions found.")
        return
    
    # Calculate Unrealized P&L
    unrealized_data = []
    for _, row in df.iterrows():
        curr = row['currency']
        qty = row['holdings']
        cost = row['cost_basis_nok']
        
        if qty > 1.0: # Only check if meaningful amount held
            rate = get_exchange_rate(curr, 'NOK')
            mkt_val = qty * rate
            unrealized = mkt_val - cost
        else:
            mkt_val = 0
            unrealized = 0
            
        unrealized_data.append({
            'Market Value (NOK)': mkt_val,
            'Unrealized P&L (NOK)': unrealized
        })
        
    df_unrealized = pd.DataFrame(unrealized_data)
    df_final = pd.concat([df, df_unrealized], axis=1)
    
    # Select and Rename Columns for Terminal Display
    display_df = df_final[[
        'currency', 'realized_pl_nok', 'holdings', 'cost_basis_nok', 
        'Market Value (NOK)', 'Unrealized P&L (NOK)'
    ]].copy()    
    display_df.columns = [
        'Currency', 'Realized P&L', 'Holdings', 'Cost Basis',
        'Market Value', 'Unrealized P&L'
    ]
    
    # Formatting for terminal
    pd.options.display.float_format = '{:,.2f}'.format
    print("\nFX Performance Report (NOK):")
    print(display_df.to_string(index=False))
    
    total_realized = display_df['Realized P&L'].sum()
    total_unrealized = display_df['Unrealized P&L'].sum()
    
    print("-" * 60)
    print(f"Total Realized:   {total_realized:,.2f} NOK")
    print(f"Total Unrealized: {total_unrealized:,.2f} NOK")
    print(f"Total FX P&L:     {total_realized + total_unrealized:,.2f} NOK")

if __name__ == "__main__":
    analyze_fx()
