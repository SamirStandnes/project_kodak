import streamlit as st
import pandas as pd
import sys
import os

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is scripts/analysis
project_root = os.path.dirname(os.path.dirname(current_dir)) # This is project root
sys.path.append(project_root)

from scripts.analysis.generate_summary_report import generate_summary_report

st.set_page_config(page_title="Portfolio Holdings", page_icon="📊", layout="wide")

@st.cache_data(ttl=300)
def load_holdings():
    df, _, _ = generate_summary_report(verbose=False)
    return df

st.title("📊 Current Holdings")

try:
    df = load_holdings()
except Exception as e:
    st.error(f"Error loading holdings: {e}")
    st.stop()

if not df.empty:
    # Prepare data for display
    display_df = df.copy()
    
    # Filter out empty rows/symbols if any
    display_df = display_df[display_df['Symbol'].notna() & (display_df['Symbol'] != '')]
    
    display_df['Weight'] = display_df['Weight'] * 100  # Scale for 0-100 display

    # Configuration for columns
    column_config = {
        "Symbol": st.column_config.TextColumn("Symbol", help="Ticker Symbol"),
        "Sector": st.column_config.TextColumn("Sector"),
        "Quantity": st.column_config.NumberColumn("Qty", format="%.0f"),
        "LatestPrice_NOK": st.column_config.NumberColumn("Price (NOK)", format="%.2f"),
        "MarketValue_NOK": st.column_config.NumberColumn("Market Value", format="%.0f"),
        "AvgWAC_NOK": st.column_config.NumberColumn("Avg Cost", format="%.2f"),
        "AvgReturn_pct": st.column_config.NumberColumn("Return (Avg)", format="%.2f%%"),
        "FIFOReturn_pct": st.column_config.NumberColumn("Return (FIFO)", format="%.2f%%"),
        "Weight": st.column_config.ProgressColumn(
            "Portfolio Weight", 
            format="%.2f%%", 
            min_value=0, 
            max_value=100
        ),
    }

    cols_to_show = [
        "Symbol", "Sector", "Quantity", "LatestPrice_NOK", 
        "MarketValue_NOK", "AvgWAC_NOK", "AvgReturn_pct", "FIFOReturn_pct", "Weight"
    ]

    st.dataframe(
        display_df[cols_to_show],
        use_container_width=True,
        column_config=column_config,
        hide_index=True,
        height=800
    )
else:
    st.info("No current holdings found.")
