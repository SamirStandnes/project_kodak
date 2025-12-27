import streamlit as st
import pandas as pd
import sys
import os

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is scripts/dashboard
project_root = os.path.dirname(os.path.dirname(current_dir)) # This is project root
sys.path.append(project_root)

from scripts.dashboard.sidebar import render_sidebar, load_summary_data

st.set_page_config(page_title="Portfolio Holdings", page_icon="📊", layout="wide")

render_sidebar()

st.title("📊 Current Holdings")

try:
    df, _, _ = load_summary_data()
except Exception as e:
    st.error(f"Error loading holdings: {e}")
    st.stop()

if not df.empty:
    # Prepare data for display
    display_df = df.copy()
    
    # Filter out empty rows/symbols if any
    display_df = display_df[
        display_df['Symbol'].notna() & 
        (display_df['Symbol'].astype(str).str.strip() != '')
    ]
    display_df = display_df.reset_index(drop=True)
    
    display_df['Weight'] = display_df['Weight'] * 100  # Scale for 0-100 display

    # Configuration for columns
    column_config = {
        "Symbol": st.column_config.TextColumn("Symbol", help="Ticker Symbol", width="small"),
        "Sector": st.column_config.TextColumn("Sector", width="medium"),
        "Quantity": st.column_config.NumberColumn("Qty", format="%.0f", help="Shares held"),
        "LatestPrice_NOK": st.column_config.NumberColumn("Price", format="%.2f"),
        "MarketValue_NOK": st.column_config.NumberColumn("Market Value", format="%.0f", help="Total position value in NOK"),
        "AvgWAC_NOK": st.column_config.NumberColumn("Avg Cost", format="%.2f"),
        "AvgReturn_pct": st.column_config.NumberColumn(
            "Return (Avg)", 
            format="%.2f%%",
            help="Total return based on weighted average cost"
        ),
        "FIFOReturn_pct": st.column_config.NumberColumn(
            "Return (FIFO)", 
            format="%.2f%%",
            help="Total return based on First-In-First-Out cost basis"
        ),
        "Weight": st.column_config.ProgressColumn(
            "Weight", 
            format="%.1f%%", 
            min_value=0, 
            max_value=100
        ),
    }

    cols_to_show = [
        "Symbol", "Sector", "Quantity", "LatestPrice_NOK", 
        "MarketValue_NOK", "AvgWAC_NOK", "AvgReturn_pct", "FIFOReturn_pct", "Weight"
    ]

    # Display the dataframe with better styling
    st.dataframe(
        display_df[cols_to_show],
        use_container_width=True,
        column_config=column_config,
        hide_index=True
    )
else:
    st.info("No current holdings found.")
