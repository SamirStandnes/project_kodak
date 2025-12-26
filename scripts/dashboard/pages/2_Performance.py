import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Add path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from scripts.analysis.calculate_yearly_returns import calculate_yearly_returns, calculate_rolling_returns
from scripts.analysis.generate_summary_report import generate_summary_report

st.set_page_config(page_title="Portfolio Performance", page_icon="📈", layout="wide")

st.title("📈 Portfolio Performance")

# --- Data Loading ---
@st.cache_data(ttl=3600)
def load_yearly_data():
    return calculate_yearly_returns()

@st.cache_data(ttl=3600)
def load_rolling_data():
    return calculate_rolling_returns()

@st.cache_data(ttl=300)
def load_holdings_data():
    df, _, _ = generate_summary_report(verbose=False)
    return df

# --- Rolling Returns Section ---
st.subheader("Return Summary (Annualized)")
with st.spinner("Calculating rolling returns..."):
    try:
        rolling = load_rolling_data()
        cols = st.columns(len(rolling))
        for col, (label, value) in zip(cols, rolling.items()):
            with col:
                if value is not None:
                    st.metric(label=label, value=f"{value:.2%}")
                else:
                    st.metric(label=label, value="N/A")
    except Exception as e:
        st.error(f"Error calculating rolling returns: {e}")

st.markdown("---")

# --- Yearly Returns Section ---
st.subheader("Yearly Returns (XIRR)")
with st.spinner("Calculating historical performance..."):
    try:
        data = load_yearly_data()
        if data:
            df_yearly = pd.DataFrame(data)
            df_yearly['Return_Pct'] = df_yearly['Return'] * 100
            
            fig = px.bar(
                df_yearly, 
                x='Year', 
                y='Return_Pct',
                text_auto='.2f',
                labels={'Return_Pct': 'Return (%)'},
                color='Return_Pct',
                color_continuous_scale=['red', 'yellow', 'green'],
                range_color=[-20, 30]
            )
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction history available to calculate returns.")
    except Exception as e:
        st.error(f"Error calculating returns: {e}")

st.markdown("---")

# --- Breakdown Performance Section ---
st.subheader("Current Performance Breakdown")

def plot_performance_by_group(df, group_col, title):
    if df.empty:
        return None
        
    perf_data = []
    for group_name, group in df.groupby(group_col):
        total_market_val = group['MarketValue_NOK'].sum()
        total_cost_basis = group['AvgCostBasis_NOK'].sum()
        
        if total_cost_basis > 0:
            avg_return = (total_market_val / total_cost_basis - 1) * 100
        else:
            avg_return = 0
        
        perf_data.append({
            group_col: group_name,
            'Return_Pct': avg_return,
            'Total_Value': total_market_val
        })
    
    if not perf_data:
        return None

    df_perf = pd.DataFrame(perf_data).sort_values(by='Return_Pct', ascending=False)
    
    fig = px.bar(
        df_perf,
        x=group_col,
        y='Return_Pct',
        text_auto='.2f',
        color='Return_Pct',
        color_continuous_scale='RdYlGn',
        labels={'Return_Pct': 'Return (%)', 'Total_Value': 'Market Value (NOK)'},
        hover_data={'Total_Value': ':,.0f'},
        title=title
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig

try:
    holdings_df = load_holdings_data()
    if not holdings_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_sector = plot_performance_by_group(holdings_df, 'Sector', "By Sector")
            if fig_sector:
                st.plotly_chart(fig_sector, use_container_width=True)
            else:
                st.info("No sector data available.")
                
        with col2:
            fig_region = plot_performance_by_group(holdings_df, 'Region', "By Region")
            if fig_region:
                st.plotly_chart(fig_region, use_container_width=True)
            else:
                st.info("No region data available.")
        
    else:
        st.info("No holdings data available for detailed analysis.")
except Exception as e:
    st.error(f"Error calculating breakdown performance: {e}")
