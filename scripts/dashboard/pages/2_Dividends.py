import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.shared.calculations import get_dividend_details
from scripts.shared.utils import load_config

# --- CONFIGURATION ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

st.set_page_config(page_title="Dividend Analysis", page_icon="💰", layout="wide")

st.title(f"💰 Dividend Analysis ({BASE_CURRENCY})")

@st.cache_data
def load_dividend_data():
    return get_dividend_details()

df_yearly, df_2025, df_all_time = load_dividend_data()

# Charts & Tables
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Dividends by Year ({BASE_CURRENCY})")
    st.bar_chart(df_yearly.set_index('year'), color="#2ecc71")

with col2:
    st.subheader(f"Top Payers (Current Year) - {BASE_CURRENCY}")
    st.dataframe(
        df_2025,
        column_config={
            "symbol": st.column_config.TextColumn("Instrument"),
            "total": st.column_config.NumberColumn(f"Total ({BASE_CURRENCY})", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.subheader(f"Top Payers (All Time) - {BASE_CURRENCY}")
st.dataframe(
    df_all_time.head(30),
    column_config={
        "symbol": st.column_config.TextColumn("Instrument"),
        "total": st.column_config.NumberColumn(f"Total Payout ({BASE_CURRENCY})", format="%.0f"),
    },
    use_container_width=True,
    hide_index=True
)
