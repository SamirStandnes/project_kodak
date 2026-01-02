import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scripts.shared.calculations import get_yearly_equity_curve, get_yearly_contribution, get_total_xirr

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")

st.title("📈 Portfolio Performance")

# --- 1. All-Time Stats ---
with st.spinner("Calculating All-Time Performance..."):
    total_xirr = get_total_xirr()

st.metric("All-Time XIRR (Annualized)", f"{total_xirr:.2f}%")
st.divider()

# --- 2. Yearly Timeline ---
with st.spinner("Fetching Yearly Data..."):
    df_years, missing_prices = get_yearly_equity_curve()

if not df_years.empty:
    # Chart: Equity Curve (Bar for Equity, Line for Return?)
    # Let's do a Combo Chart: Bars = End Equity, Line = XIRR %
    
    fig = go.Figure()
    
    # Bar: End Equity
    fig.add_trace(go.Bar(
        x=df_years['year'],
        y=df_years['end_equity'],
        name='End Equity (NOK)',
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
        yaxis=dict(title='Equity (NOK)', side='left', showgrid=False),
        yaxis2=dict(title='Return (%)', side='right', overlaying='y', showgrid=True),
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("Yearly Summary")
    st.dataframe(
        df_years.style.format({
            "start_equity": "{:,.0f}",
            "net_flow": "{:,.0f}",
            "end_equity": "{:,.0f}",
            "profit": "{:,.0f}",
            "return_pct": "{:.2f}%"
        }),
        use_container_width=True
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
        df_contrib, year_xirr, missing_prices_year = get_yearly_contribution(selected_year)
    
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
            df_contrib.style.format({
                "SOY Value": "{:,.0f}",
                "Net Additions": "{:,.0f}",
                "EOY Value": "{:,.0f}",
                "Dividends": "{:,.0f}",
                "Profit": "{:,.0f}",
                "IRR %": "{:.1f}%",
                "Contribution %": "{:.2f}%"
            }),
            use_container_width=True
        )
        
        if missing_prices_year:
            with st.expander(f"⚠️ Missing / Fallback Prices for {selected_year}"):
                 st.dataframe(pd.DataFrame(missing_prices_year))
