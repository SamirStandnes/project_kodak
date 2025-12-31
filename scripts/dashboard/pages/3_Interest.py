import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from scripts.shared.calculations import get_interest_details

st.set_page_config(page_title="Interest Expense", page_icon="💸", layout="wide")

st.title("💸 Interest Expense Analysis")

@st.cache_data
def load_interest_data():
    return get_interest_details()

df_yearly, df_currency, df_top = load_interest_data()

# Summary
total_interest = df_yearly['total'].sum()
st.metric("Total Interest Paid (All Time)", f"{total_interest:,.1f} NOK")

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
        "amount": st.column_config.NumberColumn(format="%.1f"),
        "amount_local": st.column_config.NumberColumn(format="%.1f"),
    },
    use_container_width=True,
    hide_index=True
)
