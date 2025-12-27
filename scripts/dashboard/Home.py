import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import sqlite3

# Add the parent directory to sys.path to allow imports from scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from scripts.dashboard.sidebar import render_sidebar, load_summary_data, check_staging_status

st.set_page_config(
    page_title="Kodak Portfolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
render_sidebar()

# --- Main Layout ---
st.title("Portfolio Overview")

with st.spinner('Loading portfolio data...'):
    try:
        holdings_df, summary_data, unpriced_securities = load_summary_data()
        staging_count = check_staging_status()
    except Exception as e:
        st.error(f"Error loading summary data: {e}")
        st.stop()

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    tmv = summary_data['total_market_value']
    tmv_str = f"{tmv/1e6:,.2f}M NOK".replace(',', ' ')
    st.metric(
        label="Total Market Value",
        value=tmv_str,
    )

with col2:
    change = summary_data['total_avg_gain_loss']
    st.metric(
        label="Unrealized Gain (Avg)",
        value=f"{change/1e6:,.2f}M NOK".replace(',', ' '),
        delta=f"{summary_data['total_avg_return_pct']:.2f}%"
    )

with col3:
    change_fifo = summary_data['total_fifo_gain_loss']
    st.metric(
        label="Unrealized Gain (FIFO)",
        value=f"{change_fifo/1e6:,.2f}M NOK".replace(',', ' '),
        delta=f"{summary_data['total_fifo_return_pct']:.2f}%"
    )

with col4:
    st.metric(
        label="Portfolio IRR (XIRR)",
        value=f"{summary_data['cagr_xirr']:.2%}",
        help="Annualized internal rate of return accounting for cash flows and margin debt."
    )

st.markdown("---")

# Visual Overview
col_charts_1, col_charts_2 = st.columns(2)

with col_charts_1:
    st.subheader("Sector Allocation")
    if not holdings_df.empty:
        fig_sector = px.pie(
            holdings_df, 
            values='MarketValue_NOK', 
            names='Sector', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        st.plotly_chart(fig_sector, use_container_width=True)
    else:
        st.info("No holdings data available.")

with col_charts_2:
    st.subheader("Quick Stats")
    cash_bal = summary_data.get('current_cash_balance', 0)
    st.markdown(f"""
    - **Net Cash Balance:** {cash_bal/1e6:,.2f}M NOK
    - **Total Dividends:** {summary_data['total_dividends']/1e6:,.2f}M NOK
    - **Total Fees Paid:** {abs(summary_data['total_fees']):,.0f} NOK
    - **Total Interest:** {abs(summary_data['total_interest_paid']):,.0f} NOK
    - **Active Positions:** {len(holdings_df)}
    """.replace(',', ' '))
