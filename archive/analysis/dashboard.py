import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import sqlite3

# Add the parent directory to sys.path to allow imports from scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# Import existing analysis logic
from scripts.analysis.generate_summary_report import generate_summary_report
from scripts.analysis.calculate_yearly_returns import calculate_yearly_returns

st.set_page_config(
    page_title="Kodak Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Data Loading with Caching ---

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_summary_data():
    """
    Wraps the generate_summary_report function.
    """
    df, summary, unpriced = generate_summary_report(verbose=False)
    return df, summary, unpriced

@st.cache_data(ttl=3600) # Cache for 1 hour (expensive calculation)
def load_yearly_returns():
    """
    Wraps the calculate_yearly_returns function.
    """
    return calculate_yearly_returns()

@st.cache_data(ttl=60)
def load_recent_transactions(limit=20):
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    conn = sqlite3.connect(db_file)
    query = f"""
        SELECT TradeDate, Type, Symbol, Quantity, Price, Amount_Base, Source 
        FROM transactions 
        ORDER BY TradeDate DESC, GlobalID DESC 
        LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def check_staging_status():
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    conn = sqlite3.connect(db_file)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions_staging")
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        # Table might not exist if no staging has ever happened or DB is fresh
        count = 0
    conn.close()
    return count

# --- Dashboard Layout ---

st.title("Kodak Portfolio Dashboard")

# Load data
with st.spinner('Crunching the numbers...'):
    try:
        holdings_df, summary_data, unpriced_securities = load_summary_data()
        staging_count = check_staging_status()
    except Exception as e:
        st.error(f"Error loading summary data: {e}")
        st.stop()

# Sidebar
st.sidebar.header("Status")
if staging_count > 0:
    st.sidebar.warning(f"⚠️ {staging_count} transactions in Staging")
    st.sidebar.info("Run `python scripts/db/review_staging.py` to review.")
else:
    st.sidebar.success("✅ Staging Area Empty")

if unpriced_securities:
    st.sidebar.warning(f"⚠️ {len(unpriced_securities)} Unpriced Securities")
    with st.sidebar.expander("See List"):
        for item in unpriced_securities:
            st.write(f"- {item}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Last Data Update:**")
if summary_data.get('last_trade_dates_by_source'):
    for source, date_str in summary_data['last_trade_dates_by_source'].items():
        st.sidebar.text(f"{source}: {date_str}")


# Top Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Market Value",
        value=f"{summary_data['total_market_value']:,.0f} NOK",
    )

with col2:
    change = summary_data['total_avg_gain_loss']
    st.metric(
        label="Total Gain/Loss (Avg)",
        value=f"{change:,.0f} NOK",
        delta=f"{summary_data['total_avg_return_pct']:.2f}%"
    )

with col3:
    change_fifo = summary_data['total_fifo_gain_loss']
    st.metric(
        label="Total Gain/Loss (FIFO)",
        value=f"{change_fifo:,.0f} NOK",
        delta=f"{summary_data['total_fifo_return_pct']:.2f}%"
    )

with col4:
    st.metric(
        label="Annualized Return (XIRR)",
        value=f"{summary_data['cagr_xirr']:.2%}",
    )

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Holdings", "📈 Performance & Charts", "🕒 Recent Activity", "ℹ️ Info"])

with tab1:
    st.subheader("Current Holdings")
    
    if not holdings_df.empty:
        # Formatting for display
        display_df = holdings_df.copy()
        
        # Select columns to show
        cols_to_show = [
            "Symbol", "Sector", "Quantity", "LatestPrice_NOK", 
            "MarketValue_NOK", "AvgWAC_NOK", "AvgReturn_pct", "FIFOReturn_pct", "Weight"
        ]

        # Convert Weight to percentage (0-100) for better display scaling
        display_df['Weight'] = display_df['Weight'] * 100
        
        # Rename for cleaner headers
        column_config = {
            "LatestPrice_NOK": st.column_config.NumberColumn("Price (NOK)", format="%.2f"),
            "MarketValue_NOK": st.column_config.NumberColumn("Market Value (NOK)", format="%.0f"),
            "AvgWAC_NOK": st.column_config.NumberColumn("Avg Cost", format="%.2f"),
            "AvgReturn_pct": st.column_config.NumberColumn("Avg Return", format="%.2f%%"),
            "FIFOReturn_pct": st.column_config.NumberColumn("FIFO Return", format="%.2f%%"),
            "Weight": st.column_config.ProgressColumn("Portfolio Weight", format="%.2f%%", min_value=0, max_value=100),
            "Quantity": st.column_config.NumberColumn("Qty", format="%.0f"),
        }

        st.dataframe(
            display_df[cols_to_show],
            use_container_width=True,
            column_config=column_config,
            hide_index=True,
            height=600
        )
    else:
        st.info("No holdings found.")

with tab2:
    col_charts_1, col_charts_2 = st.columns([1, 1])
    
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
    
    with col_charts_2:
        st.subheader("Yearly Returns (XIRR)")
        # Lazy load yearly returns as it might take time
        with st.spinner('Calculating historical yearly returns... (this may take a moment)'):
            try:
                yearly_data = load_yearly_returns()
                if yearly_data:
                    ydf = pd.DataFrame(yearly_data)
                    ydf['Return_Pct'] = ydf['Return'] * 100
                    
                    fig_yearly = px.bar(
                        ydf, 
                        x='Year', 
                        y='Return_Pct',
                        text_auto='.2f',
                        color='Return_Pct',
                        color_continuous_scale=['red', 'yellow', 'green'],
                        range_color=[-10, 20] # Adjust based on expected range
                    )
                    fig_yearly.update_layout(yaxis_title="Return (%)", coloraxis_showscale=False)
                    st.plotly_chart(fig_yearly, use_container_width=True)
                else:
                    st.info("No historical data available for yearly returns.")
            except Exception as e:
                st.error(f"Could not calculate yearly returns: {e}")

with tab3:
    st.subheader("Last 20 Transactions")
    recent_tx = load_recent_transactions()
    st.dataframe(recent_tx, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Portfolio Info")
    st.markdown(f"""
    - **Total Fees Paid:** {summary_data['total_fees']:,.0f} NOK
    - **Total Dividends Received:** {summary_data['total_dividends']:,.0f} NOK
    - **Total Interest Paid:** {summary_data['total_interest_paid']:,.0f} NOK
    """)
