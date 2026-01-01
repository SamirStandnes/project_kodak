import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from scripts.shared.calculations import get_fx_performance
from scripts.shared.market_data import get_exchange_rate

st.set_page_config(page_title="FX Analysis", page_icon="💱", layout="wide")

st.title("💱 Currency Exchange Analysis")

@st.cache_data
def load_fx_data():
    df = get_fx_performance()
    if df.empty:
        return df
    
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
            'market_value_nok': mkt_val,
            'unrealized_pl_nok': unrealized
        })
        
    df_unrealized = pd.DataFrame(unrealized_data)
    df_final = pd.concat([df, df_unrealized], axis=1)
    
    return df_final

df = load_fx_data()

if df.empty:
    st.info("No currency exchange transactions found.")
else:
    # Summary Metrics
    total_realized = df['realized_pl_nok'].sum()
    total_unrealized = df['unrealized_pl_nok'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Realized FX Gain", f"{total_realized:,.0f} NOK")
    col2.metric("Total Unrealized FX Gain", f"{total_unrealized:,.0f} NOK")
    col3.metric("Total FX P&L", f"{total_realized + total_unrealized:,.0f} NOK")
    
    st.divider()
    
    # Detailed Table
    st.subheader("Performance by Currency")
    st.dataframe(
        df,
        column_config={
            "currency": st.column_config.TextColumn("Currency"),
            "realized_pl_nok": st.column_config.NumberColumn("Realized P&L (NOK)", format="%.0f"),
            "holdings": st.column_config.NumberColumn("Current Holdings (Qty)", format="%.2f"),
            "cost_basis_nok": st.column_config.NumberColumn("Cost Basis (NOK)", format="%.0f"),
            "market_value_nok": st.column_config.NumberColumn("Market Value (NOK)", format="%.0f"),
            "unrealized_pl_nok": st.column_config.NumberColumn("Unrealized P&L (NOK)", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True
    )
