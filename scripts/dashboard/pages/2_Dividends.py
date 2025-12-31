import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.shared.db import get_connection

st.set_page_config(page_title="Dividend Analysis", page_icon="💰", layout="wide")

st.title("💰 Dividend Analysis")

@st.cache_data
def load_dividend_data():
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
    df_2025 = pd.read_sql_query("""
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
    return df_yearly, df_2025, df_all_time

df_yearly, df_2025, df_all_time = load_dividend_data()

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Dividends by Year")
    st.bar_chart(df_yearly.set_index('year'))

with col2:
    st.subheader("Top Payers (2025)")
    fig = px.pie(df_2025.head(10), values='total', names='symbol', title='2025 Dividend Composition')
    st.plotly_chart(fig, use_container_width=True)

# Tables
col3, col4 = st.columns(2)

with col3:
    st.subheader("Top Payers (All Time)")
    st.dataframe(
        df_all_time.head(15),
        column_config={
            "total": st.column_config.NumberColumn(format="%.0f NOK"),
        },
        use_container_width=True,
        hide_index=True
    )

with col4:
    st.subheader("Top Payers (2025)")
    st.dataframe(
        df_2025,
        column_config={
            "total": st.column_config.NumberColumn(format="%.0f NOK"),
        },
        use_container_width=True,
        hide_index=True
    )
