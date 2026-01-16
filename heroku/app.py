"""
Heroku Streamlit Dashboard - Main Entry Point

This is the cloud-ready version of the Kodak portfolio dashboard.
It uses PostgreSQL instead of SQLite and includes password protection.
"""
import streamlit as st
import os

# --- PASSWORD AUTHENTICATION ---
def check_password():
    """Returns True if the user has entered the correct password."""

    def password_entered():
        """Checks whether the password entered by the user is correct."""
        if st.session_state.get("password") == os.environ.get("DASHBOARD_PASSWORD", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # First run or password not yet checked
    if "password_correct" not in st.session_state:
        st.set_page_config(
            page_title="Kodak Portfolio",
            page_icon="🔒",
            layout="centered"
        )
        st.title("🔒 Kodak Portfolio")
        st.text_input(
            "Enter password to access the dashboard:",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.info("This is a private portfolio dashboard.")
        return False

    # Password was entered but is incorrect
    elif not st.session_state["password_correct"]:
        st.set_page_config(
            page_title="Kodak Portfolio",
            page_icon="🔒",
            layout="centered"
        )
        st.title("🔒 Kodak Portfolio")
        st.text_input(
            "Enter password to access the dashboard:",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("😕 Incorrect password. Please try again.")
        return False

    # Password is correct
    return True


# --- MAIN APPLICATION ---
if check_password():
    # Initialize adapters BEFORE importing any kodak modules
    import heroku.setup_adapters  # noqa: F401 - Side effect import

    # Now import the dashboard modules
    import pandas as pd
    import plotly.express as px

    from kodak.shared.db import get_db_connection, execute_query
    from kodak.shared.calculations import get_holdings, get_income_and_costs
    from kodak.shared.market_data import get_exchange_rate
    from kodak.shared.utils import load_config, format_local

    # --- CONFIGURATION ---
    config = load_config()
    BASE_CURRENCY = config.get('base_currency', 'NOK')

    st.set_page_config(
        page_title=f"Kodak Portfolio ({BASE_CURRENCY})",
        page_icon="📈",
        layout="wide"
    )

    # Sidebar with logout option
    with st.sidebar:
        st.title("Kodak Portfolio")
        st.caption(f"Base Currency: {BASE_CURRENCY}")

        if st.button("🔒 Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

        st.divider()

        # Navigation
        page = st.radio(
            "Navigate to:",
            ["Overview", "Holdings", "Dividends", "Interest", "Fees", "Activity", "FX Analysis", "Performance"],
            label_visibility="collapsed"
        )

    # --- PAGE: OVERVIEW ---
    if page == "Overview":
        st.title("Portfolio Overview")

        @st.cache_data(ttl=300)
        def load_summary_data():
            with get_db_connection() as conn:
                df_holdings = get_holdings()

                instruments = pd.read_sql_query('''
                    SELECT id, sector, region, country, asset_class
                    FROM instruments
                ''', conn)

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

            price_map = {row['instrument_id']: {'price': row['close'], 'currency': row['currency']} for _, row in prices.iterrows()}
            meta_map = instruments.set_index('id').to_dict('index')

            total_market_value = 0
            total_cost = 0
            fx_cache = {}
            allocation_data = []

            for _, row in df_holdings.iterrows():
                inst_id = row['instrument_id']
                mkt = price_map.get(inst_id)
                meta = meta_map.get(inst_id, {})

                if mkt:
                    curr = mkt['currency']
                    price = mkt['price']

                    if curr == BASE_CURRENCY:
                        rate = 1.0
                    else:
                        if curr not in fx_cache:
                            fx_cache[curr] = get_exchange_rate(curr, BASE_CURRENCY)
                        rate = fx_cache[curr]

                    val = row['quantity'] * price * rate
                    total_market_value += val
                    total_cost += row['cost_basis_local']

                    allocation_data.append({
                        'Market Value': val,
                        'Sector': meta.get('sector') or 'Unknown',
                        'Region': meta.get('region') or 'Unknown',
                        'Asset Class': meta.get('asset_class') or 'Equity'
                    })

            with get_db_connection() as conn:
                cash_rows = pd.read_sql_query("SELECT currency, SUM(amount) as total FROM transactions GROUP BY currency", conn)

            total_cash_base = 0
            for _, row in cash_rows.iterrows():
                curr = row['currency']
                amt = row['total']
                if curr == BASE_CURRENCY:
                    total_cash_base += amt
                else:
                    if curr not in fx_cache:
                        fx_cache[curr] = get_exchange_rate(curr, BASE_CURRENCY)
                    total_cash_base += amt * fx_cache[curr]

            income = get_income_and_costs()

            return {
                "market_value": total_market_value,
                "cost_basis": total_cost,
                "cash": total_cash_base,
                "dividends": income['dividends'],
                "interest": income['interest'],
                "fees": income['fees'],
                "allocation": pd.DataFrame(allocation_data)
            }

        data = load_summary_data()

        # Net Wealth Overview
        st.subheader("Net Equity Overview")
        col1, col2, col3 = st.columns(3)

        net_worth = data['market_value'] + data['cash']
        total_gain = data['market_value'] - data['cost_basis']
        total_return_pct = (data['market_value'] / data['cost_basis'] - 1) * 100 if data['cost_basis'] > 0 else 0

        col1.metric("Total Net Equity", format_local(net_worth))
        col2.metric("Stock Holdings", format_local(data['market_value']))
        col3.metric("Cash & Margin", format_local(data['cash']), help="Negative value indicates margin usage.")

        # Performance & Growth
        st.subheader("Performance & Growth")
        col4, col5, col6 = st.columns(3)

        col4.metric("Unrealized Gain/Loss", format_local(total_gain), f"{format_local(total_return_pct, 2)}%", delta_color="normal")
        col5.metric("Invested Capital (Cost Basis)", format_local(data['cost_basis']))

        # Income & Costs
        st.subheader("Cash Flow (All Time)")
        col6, col7, col8 = st.columns(3)

        col6.metric("Total Dividends", format_local(data['dividends']), delta_color="normal")
        col7.metric("Total Interest Paid", format_local(data['interest']), delta_color="inverse")
        col8.metric("Total Fees Paid", format_local(data['fees']), delta_color="inverse")

        st.divider()

        # Allocation Charts
        st.subheader("Portfolio Allocation")
        acol1, acol2 = st.columns(2)

        df_alloc = data['allocation']
        if not df_alloc.empty:
            with acol1:
                fig_sector = px.pie(df_alloc, values='Market Value', names='Sector', title='By Sector')
                st.plotly_chart(fig_sector, use_container_width=True)
            with acol2:
                fig_region = px.pie(df_alloc, values='Market Value', names='Region', title='By Region')
                st.plotly_chart(fig_region, use_container_width=True)
        else:
            st.info("No allocation data available.")

    # --- PAGE: HOLDINGS ---
    elif page == "Holdings":
        st.title("Current Holdings")

        @st.cache_data(ttl=300)
        def load_holdings_data():
            df = get_holdings()

            with get_db_connection() as conn:
                prices = pd.read_sql_query('''
                    SELECT mp.instrument_id, mp.close, mp.date, i.currency, i.symbol, i.name
                    FROM market_prices mp
                    JOIN instruments i ON mp.instrument_id = i.id
                    WHERE (mp.instrument_id, mp.date) IN (
                        SELECT instrument_id, MAX(date)
                        FROM market_prices
                        GROUP BY instrument_id
                    )
                ''', conn)

            price_map = {row['instrument_id']: row for _, row in prices.iterrows()}

            fx_cache = {}
            rows = []

            for _, row in df.iterrows():
                inst_id = row['instrument_id']
                mkt = price_map.get(inst_id)

                if mkt is not None:
                    curr = mkt['currency']
                    price = mkt['close']

                    if curr == BASE_CURRENCY:
                        rate = 1.0
                    else:
                        if curr not in fx_cache:
                            fx_cache[curr] = get_exchange_rate(curr, BASE_CURRENCY)
                        rate = fx_cache[curr]

                    market_value = row['quantity'] * price * rate
                    gain = market_value - row['cost_basis_local']
                    gain_pct = (gain / row['cost_basis_local'] * 100) if row['cost_basis_local'] > 0 else 0

                    rows.append({
                        'Symbol': mkt['symbol'] or f"ID:{inst_id}",
                        'Name': mkt['name'] or '',
                        'Quantity': row['quantity'],
                        'Price': price,
                        'Currency': curr,
                        'Market Value': market_value,
                        'Cost Basis': row['cost_basis_local'],
                        'Gain/Loss': gain,
                        'Gain %': gain_pct
                    })

            return pd.DataFrame(rows)

        df_holdings = load_holdings_data()

        if not df_holdings.empty:
            st.dataframe(
                df_holdings.style.format({
                    'Quantity': '{:,.2f}',
                    'Price': '{:,.2f}',
                    'Market Value': '{:,.0f}',
                    'Cost Basis': '{:,.0f}',
                    'Gain/Loss': '{:,.0f}',
                    'Gain %': '{:+.1f}%'
                }),
                use_container_width=True
            )

            total_mv = df_holdings['Market Value'].sum()
            total_cost = df_holdings['Cost Basis'].sum()
            total_gain = df_holdings['Gain/Loss'].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Market Value", format_local(total_mv))
            col2.metric("Total Cost Basis", format_local(total_cost))
            col3.metric("Total Gain/Loss", format_local(total_gain))
        else:
            st.info("No holdings found.")

    # --- PAGE: DIVIDENDS ---
    elif page == "Dividends":
        st.title("Dividend Analysis")

        from kodak.shared.calculations import get_dividend_details, get_dividend_forecast

        @st.cache_data(ttl=300)
        def load_dividend_data():
            details = get_dividend_details()
            forecast = get_dividend_forecast()
            return details, forecast

        details, forecast = load_dividend_data()

        if not details.empty:
            st.subheader("Dividend History")
            st.dataframe(details, use_container_width=True)

            total = details['amount_local'].sum() if 'amount_local' in details.columns else 0
            st.metric("Total Dividends Received", format_local(total))

        if not forecast.empty:
            st.subheader("Dividend Forecast (Next 12 Months)")
            st.dataframe(forecast, use_container_width=True)

    # --- PAGE: INTEREST ---
    elif page == "Interest":
        st.title("Interest Analysis")

        from kodak.shared.calculations import get_interest_details

        @st.cache_data(ttl=300)
        def load_interest_data():
            return get_interest_details()

        details = load_interest_data()

        if not details.empty:
            st.dataframe(details, use_container_width=True)
            total = details['amount_local'].sum() if 'amount_local' in details.columns else 0
            st.metric("Total Interest Paid", format_local(total))
        else:
            st.info("No interest transactions found.")

    # --- PAGE: FEES ---
    elif page == "Fees":
        st.title("Fee Analysis")

        from kodak.shared.calculations import get_fee_details, get_fee_analysis

        @st.cache_data(ttl=300)
        def load_fee_data():
            details = get_fee_details()
            analysis = get_fee_analysis()
            return details, analysis

        details, analysis = load_fee_data()

        if not analysis.empty:
            st.subheader("Fee Summary by Type")
            st.dataframe(analysis, use_container_width=True)

        if not details.empty:
            st.subheader("Fee Details")
            st.dataframe(details, use_container_width=True)

            total = details['fee_local'].sum() if 'fee_local' in details.columns else 0
            st.metric("Total Fees Paid", format_local(total))

    # --- PAGE: ACTIVITY ---
    elif page == "Activity":
        st.title("Transaction Activity")

        @st.cache_data(ttl=300)
        def load_activity_data():
            with get_db_connection() as conn:
                df = pd.read_sql_query('''
                    SELECT
                        t.date,
                        t.type,
                        i.symbol,
                        i.name,
                        t.quantity,
                        t.price,
                        t.amount,
                        t.currency,
                        t.amount_local,
                        a.name as account
                    FROM transactions t
                    LEFT JOIN instruments i ON t.instrument_id = i.id
                    LEFT JOIN accounts a ON t.account_id = a.id
                    ORDER BY t.date DESC
                    LIMIT 500
                ''', conn)
            return df

        df = load_activity_data()

        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.caption(f"Showing last 500 transactions")
        else:
            st.info("No transactions found.")

    # --- PAGE: FX ANALYSIS ---
    elif page == "FX Analysis":
        st.title("Currency Exposure & FX Performance")

        from kodak.shared.calculations import get_fx_performance_detailed

        @st.cache_data(ttl=300)
        def load_fx_data():
            return get_fx_performance_detailed()

        df = load_fx_data()

        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No FX data available.")

    # --- PAGE: PERFORMANCE ---
    elif page == "Performance":
        st.title("Portfolio Performance")

        from kodak.shared.calculations import get_total_xirr, get_yearly_contributions

        @st.cache_data(ttl=300)
        def load_performance_data():
            xirr = get_total_xirr()
            contributions = get_yearly_contributions()
            return xirr, contributions

        xirr, contributions = load_performance_data()

        st.metric("Total XIRR (Annualized Return)", f"{xirr * 100:.2f}%" if xirr else "N/A")

        if not contributions.empty:
            st.subheader("Yearly Contributions")
            st.dataframe(contributions, use_container_width=True)
