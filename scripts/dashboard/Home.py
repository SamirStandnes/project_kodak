import streamlit as st
import pandas as pd
from scripts.shared.db import get_connection, execute_query
from scripts.reporting.portfolio import get_holdings
from scripts.shared.market_data import get_exchange_rate

st.set_page_config(
    page_title="Kodak Portfolio",
    page_icon="📈",
    layout="wide"
)

st.title("Project Kodak: Portfolio Overview")

# --- DATA FETCHING ---
@st.cache_data
def load_summary_data():
    conn = get_connection()
    
    # 1. Holdings & Market Value
    df_holdings = get_holdings()
    
    # Get latest prices
    prices = pd.read_sql_query('''
        SELECT mp.instrument_id, mp.close, i.currency
        FROM market_prices mp
        JOIN instruments i ON mp.instrument_id = i.id
        WHERE (mp.instrument_id, mp.date) IN (
            SELECT instrument_id, MAX(date) 
            FROM market_prices 
            GROUP BY instrument_id
        )
    ''', conn)
    
    price_map = {}
    for _, row in prices.iterrows():
        price_map[row['instrument_id']] = {'price': row['close'], 'currency': row['currency']}
        
    # Calculate Market Value
    total_market_value = 0
    total_cost = 0
    fx_cache = {}
    
    for _, row in df_holdings.iterrows():
        inst_id = row['instrument_id']
        mkt = price_map.get(inst_id)
        if mkt:
            curr = mkt['currency']
            price = mkt['price']
            
            # FX Conversion
            if curr == 'NOK':
                rate = 1.0
            else:
                if curr not in fx_cache:
                    fx_cache[curr] = get_exchange_rate(curr, 'NOK')
                rate = fx_cache[curr]
            
            val = row['quantity'] * price * rate
            total_market_value += val
            total_cost += row['cost_basis_local']

    # 2. Cash Balance (Approximate)
    cash_rows = pd.read_sql_query("SELECT currency, SUM(amount) as total FROM transactions GROUP BY currency", conn)
    total_cash_nok = 0
    for _, row in cash_rows.iterrows():
        curr = row['currency']
        amt = row['total']
        if curr == 'NOK':
            total_cash_nok += amt
        else:
            if curr not in fx_cache:
                fx_cache[curr] = get_exchange_rate(curr, 'NOK')
            total_cash_nok += amt * fx_cache[curr]

    # 3. Income Totals
    income = pd.read_sql_query('''
        SELECT 
            SUM(CASE WHEN type = 'DIVIDEND' THEN amount_local ELSE 0 END) as dividends,
            SUM(CASE WHEN type = 'INTEREST' THEN amount_local ELSE 0 END) as interest,
            SUM(CASE WHEN type = 'FEE' THEN amount_local ELSE 0 END) as fees
        FROM transactions
    ''', conn).iloc[0]

    conn.close()
    
    return {
        "market_value": total_market_value,
        "cost_basis": total_cost,
        "cash": total_cash_nok,
        "dividends": income['dividends'] or 0,
        "interest": income['interest'] or 0,
        "fees": income['fees'] or 0
    }

data = load_summary_data()

# --- METRICS DISPLAY ---

# Row 1: The Big Numbers
col1, col2, col3 = st.columns(3)

net_worth = data['market_value'] + data['cash']
total_gain = data['market_value'] - data['cost_basis']
total_return_pct = (data['market_value'] / data['cost_basis'] - 1) * 100 if data['cost_basis'] > 0 else 0

col1.metric("Net Worth", f"{net_worth:,.0f} NOK")
col2.metric("Portfolio Value (Stocks)", f"{data['market_value']:,.0f} NOK")
col3.metric("Estimated Cash", f"{data['cash']:,.0f} NOK")

# Row 2: Performance & Income
col4, col5, col6, col7 = st.columns(4)

col4.metric("Unrealized Gain", f"{total_gain:,.0f} NOK", f"{total_return_pct:.2f}%")
col5.metric("Total Dividends", f"{data['dividends']:,.0f} NOK")
col6.metric("Total Interest", f"{data['interest']:,.0f} NOK")
col7.metric("Total Fees", f"{data['fees']:,.0f} NOK")

st.divider()

st.info("💡 **Tip:** Use the sidebar to navigate to detailed views for Holdings, Dividends, Interest, and Fees.")
