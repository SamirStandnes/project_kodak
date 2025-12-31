import streamlit as st
import pandas as pd
import sys
from pathlib import Path
# Add project root to sys.path
root_path = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import streamlit as st
import pandas as pd
from scripts.shared.db import get_connection
from scripts.shared.calculations import get_holdings
from scripts.shared.market_data import get_exchange_rate

st.set_page_config(page_title="Current Holdings", page_icon="💼", layout="wide")

st.title("💼 Current Holdings")

@st.cache_data
def load_holdings_data():
    conn = get_connection()
    df_holdings = get_holdings()
    
    # Get latest prices and metadata
    prices = pd.read_sql_query('''
        SELECT mp.instrument_id, mp.close, i.currency, COALESCE(i.symbol, i.isin) as symbol, 
               i.name, i.sector, i.region, i.country, i.asset_class
        FROM market_prices mp
        JOIN instruments i ON mp.instrument_id = i.id
        WHERE (mp.instrument_id, mp.date) IN (
            SELECT instrument_id, MAX(date) 
            FROM market_prices 
            GROUP BY instrument_id
        )
    ''', conn)
    
    conn.close()
    
    price_map = {}
    for _, row in prices.iterrows():
        price_map[row['instrument_id']] = {
            'price': row['close'], 
            'currency': row['currency'],
            'name': row['name'],
            'sector': row['sector'],
            'region': row['region'],
            'country': row['country'],
            'asset_class': row['asset_class']
        }
        
    data = []
    fx_cache = {}
    total_val = 0
    
    for _, row in df_holdings.iterrows():
        inst_id = row['instrument_id']
        mkt = price_map.get(inst_id)
        
        if not mkt:
            continue # Skip unpriced (handled by gap check)
            
        curr = mkt['currency']
        price = mkt['price']
        
        # FX
        if curr == 'NOK':
            rate = 1.0
        else:
            if curr not in fx_cache:
                fx_cache[curr] = get_exchange_rate(curr, 'NOK')
            rate = fx_cache[curr]
            
        market_val_nok = row['quantity'] * price * rate
        cost_basis = row['cost_basis_local']
        gain = market_val_nok - cost_basis
        ret_pct = (market_val_nok / cost_basis - 1) * 100 if cost_basis > 0 else 0
        
        total_val += market_val_nok
        
        data.append({
            "Symbol": row['symbol'],
            "Name": mkt['name'],
            "Sector": mkt['sector'],
            "Region": mkt['region'],
            "Country": mkt['country'],
            "Type": mkt['asset_class'],
            "Qty": row['quantity'],
            "Price": price,
            "Currency": curr,
            "Market Value (NOK)": market_val_nok,
            "Avg Cost": cost_basis / row['quantity'],
            "Gain/Loss": gain,
            "Return %": ret_pct
        })
        
    df = pd.DataFrame(data)
    
    # Calculate Weight
    if not df.empty:
        df['Weight %'] = (df['Market Value (NOK)'] / total_val) * 100
        
    return df.sort_values('Market Value (NOK)', ascending=False)

df = load_holdings_data()

# Summary Metrics for this page
st.metric("Total Equity Value", f"{df['Market Value (NOK)'].sum():,.0f} NOK")

# Styling the dataframe
st.dataframe(
    df,
    column_config={
        "Qty": st.column_config.NumberColumn(format="%.2f"),
        "Price": st.column_config.NumberColumn(format="%.2f"),
        "Market Value (NOK)": st.column_config.NumberColumn(format="%.0f NOK"),
        "Avg Cost": st.column_config.NumberColumn(format="%.2f"),
        "Gain/Loss": st.column_config.NumberColumn(format="%.0f NOK"),
        "Return %": st.column_config.NumberColumn(format="%.2f%%"),
        "Weight %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
    },
    use_container_width=True,
    hide_index=True,
    height=600
)
