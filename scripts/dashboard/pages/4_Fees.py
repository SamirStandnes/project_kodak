import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from scripts.shared.db import get_connection

st.set_page_config(page_title="Fee Analysis", page_icon="🧾", layout="wide")

st.title("🧾 Fee Analysis")

@st.cache_data
def load_fee_data():
    conn = get_connection()
    
    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY year
        ORDER BY year
    """, conn)
    
    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT 
            currency, 
            SUM(
                CASE 
                    WHEN type = 'FEE' THEN ABS(amount_local) 
                    ELSE fee_local 
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY currency
        ORDER BY total ASC
    """, conn)
    
    conn.close()
    return df_yearly, df_currency

df_yearly, df_currency = load_fee_data()

# Summary
total_fees = df_yearly['total'].sum()
st.metric("Total Fees Paid (All Time)", f"{total_fees:,.0f} NOK")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Fees by Year")
    st.bar_chart(df_yearly.set_index('year'))

with col2:
    st.subheader("Fees by Currency")
    st.bar_chart(df_currency.set_index('currency'))
