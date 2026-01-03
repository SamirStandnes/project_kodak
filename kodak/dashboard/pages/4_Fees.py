import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from kodak.shared.calculations import get_fee_details
from kodak.shared.utils import load_config, format_local

# --- CONFIGURATION ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

st.set_page_config(page_title="Fee Analysis", page_icon="💸", layout="wide")

st.title("💸 Fee Analysis")

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_fee_data():
    return get_fee_details()

df_yearly, df_currency, df_top = load_fee_data()

total_fees = df_yearly['total'].sum()
st.metric(f"Total Fees Paid (All Time)", format_local(total_fees))

col1, col2 = st.columns(2)

with col1:
    st.subheader("Fees by Year")
    st.bar_chart(df_yearly.set_index('year'), color="#e67e22")

with col2:
    st.subheader("Fees by Currency")
    st.dataframe(
        df_currency,
        column_config={
            "currency": st.column_config.TextColumn("Currency"),
            "total": st.column_config.NumberColumn(f"Total Fees ({BASE_CURRENCY})", format="localized"),
        },
        use_container_width=True,
        hide_index=True
    )

st.divider()
st.subheader("Recent Individual Fees")
st.dataframe(
    df_top,
    column_config={
        "date": st.column_config.DateColumn("Date"),
        "currency": st.column_config.TextColumn("Fee Currency"),
        "amount_local": st.column_config.NumberColumn(f"Fee ({BASE_CURRENCY})", format="localized"),
        "source_file": st.column_config.TextColumn("Source"),
    },
    use_container_width=True,
    hide_index=True
)
