import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from scripts.shared.calculations import get_fee_details

st.set_page_config(page_title="Fee Analysis", page_icon="🧾", layout="wide")

st.title("🧾 Fee Analysis")

@st.cache_data
def load_fee_data():
    return get_fee_details()

df_yearly, df_currency, df_top = load_fee_data()

# Summary
total_fees = df_yearly['total'].sum()
st.metric("Total Fees Paid (All Time)", f"{total_fees:,.1f} NOK")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Fees by Year")
    st.bar_chart(df_yearly.set_index('year'))

with col2:
    st.subheader("Fees by Currency")
    st.dataframe(
        df_currency,
        column_config={
            "currency": st.column_config.TextColumn("Currency"),
            "total": st.column_config.NumberColumn("Total Fees (NOK)", format="%.1f"),
        },
        use_container_width=True,
        hide_index=True
    )

# Table
st.subheader("Recent Fees")
st.dataframe(
    df_top,
    column_config={
        "date": st.column_config.DateColumn("Date"),
        "currency": st.column_config.TextColumn("Curr"),
        "amount_local": st.column_config.NumberColumn("Fee (NOK)", format="%.1f"),
        "source_file": st.column_config.TextColumn("Source"),
    },
    use_container_width=True,
    hide_index=True
)
