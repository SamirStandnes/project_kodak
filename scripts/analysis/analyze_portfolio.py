import pandas as pd
from scripts.shared.db import get_connection, execute_query
from scripts.shared.market_data import get_latest_prices, get_exchange_rate
from scripts.shared.calculations import get_holdings, get_income_and_costs
from scripts.shared.utils import load_config
from rich.console import Console
from rich.table import Table

# --- CONFIG ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def analyze_portfolio():
    conn = get_connection()
    console = Console()
    
    # 1. Get Current Holdings
    # ... (rest of the file)
    df_holdings = get_holdings()
    if df_holdings.empty:
        console.print("[yellow]No holdings found.[/yellow]")
        return

    # 2. Get Latest Prices & Currencies
    # We need to know the currency of the instrument to fetch the right FX rate
    # For now, we assume the instrument's currency in the DB is correct, or we infer it.
    
    price_rows = execute_query('''
        SELECT mp.instrument_id, mp.close, i.currency
        FROM market_prices mp
        JOIN instruments i ON mp.instrument_id = i.id
        WHERE (mp.instrument_id, mp.date) IN (
            SELECT instrument_id, MAX(date) 
            FROM market_prices 
            GROUP BY instrument_id
        )
    ''')
    
    price_map = {} # inst_id -> {price, currency}
    for row in price_rows:
        price_map[row['instrument_id']] = {
            'price': row['close'],
            'currency': row['currency']
        }

    # Cache FX rates to avoid spamming Yahoo
    fx_cache = {}

    # 3. Enrich Holdings with Valuation
    portfolio_data = []
    total_market_value = 0
    total_cost_basis = 0

    for _, row in df_holdings.iterrows():
        inst_id = row['instrument_id']
        market_data = price_map.get(inst_id)
        
        if not market_data:
            price_nok = 0
            price_raw = 0
            curr = 'UNK'
        else:
            price_raw = market_data['price']
            curr = market_data['currency']
            
        # Convert to Base Currency
        if curr == BASE_CURRENCY:
            price_nok = price_raw
            rate = 1.0
        else:
            if curr not in fx_cache:
                fx_cache[curr] = get_exchange_rate(curr, BASE_CURRENCY)
            rate = fx_cache[curr]
            price_nok = price_raw * rate

        market_value = row['quantity'] * price_nok
        cost_basis = row['cost_basis_local']
        
        gain_loss = market_value - cost_basis
        return_pct = (market_value / cost_basis - 1) * 100 if cost_basis > 0 else 0

        portfolio_data.append({
            'Symbol': row['symbol'] or row['isin'],
            'Qty': row['quantity'],
            'Avg Cost': cost_basis / row['quantity'],
            'Price': price_raw,
            'Currency': curr,
            'Market Value': market_value,
            'Gain/Loss': gain_loss,
            'Return %': return_pct
        })
        
        total_market_value += market_value
        total_cost_basis += cost_basis

    df_report = pd.DataFrame(portfolio_data).sort_values('Market Value', ascending=False)

    # 4. Render Table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Symbol")
    table.add_column("Qty", justify="right")
    table.add_column(f"Avg Cost ({BASE_CURRENCY})", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Curr", style="dim")
    table.add_column(f"Market Value ({BASE_CURRENCY})", justify="right", style="bold yellow")
    table.add_column("Gain/Loss", justify="right")
    table.add_column("Return %", justify="right")

    for _, row in df_report.iterrows():
        gl_style = "green" if row['Gain/Loss'] >= 0 else "red"
        
        # Format weird returns
        ret_str = f"{row['Return %']:.2f}%"
        if row['Return %'] < -99: ret_str = "-100%"
        
        table.add_row(
            row['Symbol'],
            f"{row['Qty']:,.2f}",
            f"{row['Avg Cost']:,.2f}",
            f"{row['Price']:,.2f}",
            row['Currency'],
            f"{row['Market Value']:,.0f}",
            f"[{gl_style}]{row['Gain/Loss']:,.0f}[/{gl_style}]",
            f"[{gl_style}]{ret_str}[/{gl_style}]"
        )

    console.print(table)

    # 5. Summary Metrics
    total_gl = total_market_value - total_cost_basis
    total_return = (total_market_value / total_cost_basis - 1) * 100 if total_cost_basis > 0 else 0
    
    # Calculate Cash Balance properly (Multi-currency)
    cash_by_currency = execute_query("SELECT currency, SUM(amount) as total FROM transactions GROUP BY currency")
    cash_balance_nok = 0.0
    # ... (existing query logic) ...
    for _, row in cash_rows.iterrows():
        curr = row['currency']
        amt = row['total']
        
        if curr == BASE_CURRENCY:
            cash_balance_nok += amt
        else:
            if curr not in fx_cache:
                fx_cache[curr] = get_exchange_rate(curr, BASE_CURRENCY)
            rate = fx_cache[curr]
            cash_balance_nok += amt * rate

    # Calculate Totals for Dividends, Fees, Interest
    income = get_income_and_costs()

    total_dividends = income['dividends']
    total_fees = income['fees']
    total_interest = income['interest']

    summary_table = Table(show_header=False, box=None)
    summary_table.add_row("Total Market Value", f"{total_market_value:,.0f} {BASE_CURRENCY}")
    summary_table.add_row("Total Cost Basis", f"{total_cost_basis:,.0f} {BASE_CURRENCY}")
    
    gl_color = "green" if total_gl >= 0 else "red"
    summary_table.add_row("Total Gain/Loss", f"[{gl_color}]{total_gl:,.0f} {BASE_CURRENCY}[/{gl_color}]")
    
    summary_table.add_row("Estimated Cash", f"{cash_balance_nok:,.0f} {BASE_CURRENCY}")
    summary_table.add_row("Total Net Worth", f"{(total_market_value + cash_balance_nok):,.0f} {BASE_CURRENCY}")
    
    summary_table.add_section()
    summary_table.add_row("Total Dividends", f"[green]{total_dividends:,.0f} {BASE_CURRENCY}[/green]")
    summary_table.add_row("Total Interest", f"{total_interest:,.0f} {BASE_CURRENCY}")
    summary_table.add_row("Total Fees", f"[red]{total_fees:,.0f} {BASE_CURRENCY}[/red]")
    
    console.print("\n[bold]Summary Statistics[/bold]")
    console.print(summary_table)

if __name__ == "__main__":
    analyze_portfolio()