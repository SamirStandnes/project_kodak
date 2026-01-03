import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from kodak.shared.calculations import get_yearly_equity_curve, get_yearly_contribution, get_total_xirr
from kodak.shared.utils import load_config, format_local

# --- CONFIGURATION ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")

st.title("📈 Portfolio Performance")

# --- CACHED DATA LOADERS ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_total_xirr():
    return get_total_xirr()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_yearly_equity_curve():
    return get_yearly_equity_curve()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_yearly_contribution(year: str):
    return get_yearly_contribution(year)

# --- 1. All-Time Stats ---
with st.spinner("Calculating All-Time Performance..."):
    total_xirr = load_total_xirr()

st.metric("All-Time XIRR (Annualized)", f"{format_local(total_xirr, 2)}%")
st.divider()

# --- 2. Yearly Timeline ---
with st.spinner("Fetching Yearly Data..."):
    df_years, missing_prices = load_yearly_equity_curve()

if not df_years.empty:
    # Chart: Equity Curve (Bar for Equity, Line for Return?)
    # Let's do a Combo Chart: Bars = End Equity, Line = XIRR %
    
    fig = go.Figure()
    
    # Bar: End Equity
    fig.add_trace(go.Bar(
        x=df_years['year'],
        y=df_years['end_equity'],
        name='End Equity',
        marker_color='lightblue',
        yaxis='y'
    ))
    
    # Bar: Profit (Stacked? No, separate logic)
    # Let's overlay Profit
    
    # Line: XIRR
    fig.add_trace(go.Scatter(
        x=df_years['year'],
        y=df_years['return_pct'],
        name='Annual Return (%)',
        mode='lines+markers',
        line=dict(color='firebrick', width=3),
        yaxis='y2'
    ))

    fig.update_layout(
        title='Yearly Equity & Returns',
        xaxis=dict(title='Year'),
        yaxis=dict(title='Equity', side='left', showgrid=False),
        yaxis2=dict(title='Return (%)', side='right', overlaying='y', showgrid=True),
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("Yearly Summary")
    st.dataframe(
        df_years,
        column_config={
            "year": st.column_config.TextColumn("Year"),
            "start_equity": st.column_config.NumberColumn("Start Value", format="localized"),
            "net_flow": st.column_config.NumberColumn("Net Deposits", format="localized"),
            "end_equity": st.column_config.NumberColumn("End Value", format="localized"),
            "profit": st.column_config.NumberColumn(f"Profit ({BASE_CURRENCY})", format="localized"),
            "return_pct": st.column_config.NumberColumn("XIRR %", format="%.2f%%"),
        },
        use_container_width=True,
        hide_index=True
    )

    if missing_prices:
        with st.expander("⚠️ Missing / Fallback Prices Used"):
            st.dataframe(pd.DataFrame(missing_prices))

else:
    st.info("No yearly data available.")

st.divider()

# --- 3. Detailed Year View ---
st.subheader("Detailed Analysis by Year")
selected_year = st.selectbox("Select Year", df_years['year'].sort_values(ascending=False) if not df_years.empty else [])

if selected_year:
    with st.spinner(f"Analyzing {selected_year}..."):
        df_contrib, year_xirr, missing_prices_year = load_yearly_contribution(selected_year)
    
    col1, col2 = st.columns(2)
    col1.metric(f"{selected_year} XIRR", f"{year_xirr:.2f}%")
    
    # Treemap of Contribution
    if not df_contrib.empty:
        # Filter out tiny contributions for cleaner chart
        df_tree = df_contrib[abs(df_contrib['Contribution %']) > 0.05].copy()
        df_tree['Positive'] = df_tree['Contribution %'] > 0
        
        fig_tree = px.treemap(
            df_tree,
            path=['Symbol'],
            values=abs(df_tree['Contribution %']), # Size by magnitude
            color='Contribution %',
            color_continuous_scale='RdBu',
            color_continuous_midpoint=0,
            title=f"Performance Contribution Breakdown ({selected_year})"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
        st.dataframe(
            df_contrib,
            column_config={
                "Symbol": st.column_config.TextColumn("Instrument"),
                "SOY Value": st.column_config.NumberColumn("SOY Value", format="localized"),
                "Net Additions": st.column_config.NumberColumn("Net Additions", format="localized"),
                "EOY Value": st.column_config.NumberColumn("EOY Value", format="localized"),
                "Dividends": st.column_config.NumberColumn("Divs", format="localized"),
                "Profit": st.column_config.NumberColumn("Profit", format="localized"),
                "IRR %": st.column_config.NumberColumn("IRR %", format="%.1f%%"),
                "Contribution %": st.column_config.NumberColumn("Contr. %", format="%.2f%%"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.caption("""
        **Legend & Logic:**
        - **[Items in Brackets]**: These are non-instrument totals (Fees, Interest, Tax).
        - **[Cash FX & Float]***: Represents the P&L from your uninvested cash or margin debt. 
            - *Positive:* Gain from currency strengthening while holding foreign cash (or weakening while holding debt).
            - *Negative:* Loss from currency movement or unexplained cash drift.
        """)
        
        if missing_prices_year:
            with st.expander(f"⚠️ Missing / Fallback Prices for {selected_year}"):
                 st.info("ℹ️ **Why is this list longer?**\n\nDetailed analysis requires pricing for both the **Start of Year** (to calculate opening value) and **End of Year**. The Timeline view only checks the End of Year value.")
                 st.dataframe(pd.DataFrame(missing_prices_year))
