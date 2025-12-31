import streamlit as st
import pandas as pd
from scripts.shared.db import get_connection

st.set_page_config(page_title="Interest Expense", page_icon="💸", layout="wide")

st.title("💸 Interest Expense Analysis")

@st.cache_data
def load_interest_data():
    conn = get_connection()
    
    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            SUM(amount_local) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY year
        ORDER BY year
    """, conn)
    
    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT 
            currency, 
            SUM(amount_local) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY currency
        ORDER BY total ASC
    """, conn)
    
    # 3. Largest Payments
    df_top = pd.read_sql_query("""
        SELECT 
            date, 
            currency, 
            amount, 
            amount_local
        FROM transactions
        WHERE type = 'INTEREST'
        ORDER BY amount_local ASC
        LIMIT 20
    """, conn)
    
    conn.close()
    return df_yearly, df_currency, df_top

df_yearly, df_currency, df_top = load_interest_data()

# Summary
total_interest = df_yearly['total'].sum()
st.metric("Total Interest Paid (All Time)", f"{total_interest:,.0f} NOK")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Interest by Year")
    st.bar_chart(df_yearly.set_index('year'))

with col2:
    st.subheader("Interest by Currency")
    st.bar_chart(df_currency.set_index('currency'))

# Table
st.subheader("Largest Interest Payments")
st.dataframe(
    df_top,
    column_config={
        "amount": st.column_config.NumberColumn(format="%.2f"),
        "amount_local": st.column_config.NumberColumn(format="%.2f NOK"),
    },
    use_container_width=True,
    hide_index=True
)
