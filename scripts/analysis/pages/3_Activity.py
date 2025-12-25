import streamlit as st
import pandas as pd
import sqlite3
import sys
import os

# Add path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

st.set_page_config(page_title="Portfolio Activity", page_icon="📝", layout="wide")

st.title("📝 Recent Activity")

@st.cache_data(ttl=60)
def load_transactions(limit=100):
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    conn = sqlite3.connect(db_file)
    limit_clause = f"LIMIT {limit}" if limit != -1 else ""
    query = f"""
        SELECT TradeDate, Type, Symbol, Quantity, Price, Currency_Local, Amount_Base, Source 
        FROM transactions 
        ORDER BY TradeDate DESC, GlobalID DESC 
        {limit_clause}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

try:
    col1, col2 = st.columns([1, 3])
    with col1:
        show_all = st.checkbox("Show All Transactions")

    limit = -1 if show_all else st.slider("Number of transactions to show", 10, 1000, 50)
    
    df = load_transactions(limit)
    
    if not df.empty:
        # Style the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "TradeDate": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
                "Amount_Base": st.column_config.NumberColumn("Amount (NOK)", format="%.2f"),
                "Price": st.column_config.NumberColumn("Price", format="%.2f"),
                "Quantity": st.column_config.NumberColumn("Qty", format="%.4f"),
            },
            hide_index=True
        )
    else:
        st.info("No transactions found.")

except Exception as e:
    st.error(f"Error loading transactions: {e}")