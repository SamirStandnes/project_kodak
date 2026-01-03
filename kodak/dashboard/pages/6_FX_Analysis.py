import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from kodak.shared.calculations import get_fx_performance
from kodak.shared.market_data import get_exchange_rate
from kodak.shared.utils import load_config, format_local

# --- CONFIGURATION ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

st.set_page_config(page_title="FX Analysis", page_icon="💱", layout="wide")

st.title("💱 Currency Performance")

@st.cache_data(ttl=300)  # Cache for 5 minutes
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
            # Current Rate
            rate = get_exchange_rate(curr, BASE_CURRENCY)
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
    col1.metric("Total Realized FX Gain", format_local(total_realized))
    col2.metric("Total Unrealized FX Gain", format_local(total_unrealized))
    col3.metric("Total FX P&L", format_local(total_realized + total_unrealized))
    
    st.divider()
    
    # Detailed Table
    st.subheader("Performance by Currency")
    st.dataframe(
        df,
        column_config={
            "currency": st.column_config.TextColumn("Currency"),
            "realized_pl_nok": st.column_config.NumberColumn(f"Realized P&L ({BASE_CURRENCY})", format="localized"),
            "holdings": st.column_config.NumberColumn("Current Holdings (Qty)", format="localized"),
            "cost_basis_nok": st.column_config.NumberColumn(f"Cost Basis ({BASE_CURRENCY})", format="localized"),
            "market_value_nok": st.column_config.NumberColumn(f"Market Value ({BASE_CURRENCY})", format="localized"),
            "unrealized_pl_nok": st.column_config.NumberColumn(f"Unrealized P&L ({BASE_CURRENCY})", format="localized"),
        },
        use_container_width=True,
        hide_index=True
    )
