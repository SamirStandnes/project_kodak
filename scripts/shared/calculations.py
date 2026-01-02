import pandas as pd
import numpy as np
from scripts.shared.db import get_connection, execute_query
from scripts.shared.market_data import get_historical_prices_by_date
from datetime import datetime

# --- Constants for Transaction Classification ---
INFLOW_TYPES = ['BUY', 'DEPOSIT', 'TILDELING INNLEGG RE', 'BYTTE INNLEGG VP', 'TRANSFER_IN', 'EMISJON INNLEGG VP']
OUTFLOW_TYPES = ['SELL', 'WITHDRAWAL', 'BYTTE UTTAK VP', 'TRANSFER_OUT', 'INNLØSN. UTTAK VP']

def get_internal_splits():
    """
    Discovers stock splits from 'BYTTE' (Exchange) transactions in the DB.
    Returns { symbol: [(date, ratio)] }
    """
    conn = get_connection()
    query = """
        SELECT t.date, i.symbol, t.type, t.quantity 
        FROM transactions t
        JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type LIKE 'BYTTE %'
        ORDER BY t.date, i.symbol
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    splits = {}
    # Group by date and symbol to find the IN/OUT pairs
    for (date, symbol), group in df.groupby([df['date'].str[:10], 'symbol']):
        row_in = group[group['type'] == 'BYTTE INNLEGG VP']
        row_out = group[group['type'] == 'BYTTE UTTAK VP']
        
        if not row_in.empty and not row_out.empty:
            qty_in = row_in.iloc[0]['quantity']
            qty_out = abs(row_out.iloc[0]['quantity'])
            if qty_out != 0:
                ratio = qty_in / qty_out
                if symbol not in splits: splits[symbol] = []
                splits[symbol].append((pd.to_datetime(date), ratio))
    return splits

def get_adjusted_qty(symbol, raw_qty, ref_date, split_map):
    """
    Adjusts raw quantity to today's scale based on splits occurring after ref_date.
    """
    if symbol not in split_map or raw_qty == 0:
        return raw_qty
        
    ts_ref = pd.Timestamp(ref_date)
    ratio = 1.0
    for split_date, split_ratio in split_map[symbol]:
        if split_date > ts_ref:
            ratio *= split_ratio
    return raw_qty * ratio

def xirr(transactions):
    if not transactions: return 0.0
    transactions.sort(key=lambda x: x[0])
    amounts = [t[1] for t in transactions]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts): return 0.0
    dates = [t[0] for t in transactions]; d0 = dates[0]
    years = [(d - d0).days / 365.0 for d in dates]
    rate = 0.1
    for _ in range(50):
        f = 0.0; df = 0.0
        for i, year in enumerate(years):
            a = amounts[i]; r_plus_1 = (1 + rate)
            if r_plus_1 <= 0: r_plus_1 = 1e-6 
            exp = r_plus_1 ** year
            f += a / exp
            df -= a * year * (r_plus_1 ** (year - 1)) / (exp ** 2)
        if abs(f) < 1e-6: return float(rate.real) if hasattr(rate, 'real') else float(rate)
        if df == 0: break
        new_rate = rate - f / df
        if abs(new_rate - rate) < 1e-6: return float(new_rate.real) if hasattr(new_rate, 'real') else float(new_rate)
        rate = new_rate
    return float(rate.real) if hasattr(rate, 'real') else float(rate)

def get_yearly_contribution(target_year: str):
    conn = get_connection()
    df = pd.read_sql("SELECT t.date, t.type, t.instrument_id, t.quantity, t.amount_local, t.fee_local, i.symbol, i.currency FROM transactions t LEFT JOIN instruments i ON t.instrument_id = i.id WHERE t.date <= ? ORDER BY t.date, t.id", conn, params=(f"{target_year}-12-31",))
    conn.close()
    if df.empty: return pd.DataFrame(), 0.0
    
    soy_date = f"{int(target_year)-1}-12-31"; eoy_date = f"{target_year}-12-31"
    split_map = get_internal_splits()

    # 1. External Flows (Portfolio Level)
    flow_txns = df[df['type'].isin(['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT'])].copy()
    flow_txns['date_obj'] = pd.to_datetime(flow_txns['date'], format='mixed')
    yearly_detailed_flows = {}
    for _, row in flow_txns.iterrows():
        y = str(row['date'])[:4]; d = row['date_obj']; amt = row['amount_local']
        if y not in yearly_detailed_flows: yearly_detailed_flows[y] = []
        yearly_detailed_flows[y].append((d, -amt))

    # 2. Replay Loop State
    holdings = {}; soy_holdings = {}; eoy_holdings = {}; pos_flows = {}; dividends = {}; detailed_flows = {}
    cash_soy = 0.0; cash_eoy = 0.0; cash_flows_ext = 0.0
    fees_t = 0.0; int_t = 0.0; tax_t = 0.0
    sym_currency = {}

    for _, row in df.iterrows():
        t_date = row['date'][:10]; t_date_obj = pd.to_datetime(t_date); t_year = t_date[:4]; t_type = row['type']; qty = row['quantity']; amt = row['amount_local']
        sym = row['symbol']
        
        # Track Cash
        if t_date <= soy_date: cash_soy += amt
        cash_eoy += amt
        
        if t_year == target_year:
            if t_type in ['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT']: cash_flows_ext += amt
            elif t_type == 'FEE': fees_t += amt
            elif t_type == 'INTEREST': int_t += amt
            elif t_type == 'TAX': tax_t += amt
            f_emb = row.get('fee_local', 0.0)
            if pd.notna(f_emb) and f_emb > 0: fees_t -= abs(f_emb)
        
        # Track Positions
        if sym:
            sym_currency[sym] = row['currency']
            if sym not in holdings: holdings[sym] = {'qty': 0.0, 'cost': 0.0}
            h = holdings[sym]
            
            if t_type in ['BUY', 'SELL', 'INNLØSN. UTTAK VP', 'TILDELING INNLEGG RE', 'BYTTE INNLEGG VP', 'BYTTE UTTAK VP', 'TRANSFER_IN', 'TRANSFER_OUT', 'EMISJON INNLEGG VP']:
                if t_type in INFLOW_TYPES: h['qty'] += qty; h['cost'] += abs(amt)
                elif t_type in OUTFLOW_TYPES:
                    if h['qty'] > 0: h['cost'] -= (h['cost'] / h['qty']) * abs(qty)
                    h['qty'] += qty
            
            # Save Snapshots
            if t_date <= soy_date: soy_holdings[sym] = h.copy()
            eoy_holdings[sym] = h.copy()

            if t_year == target_year and t_type in ['BUY', 'SELL', 'INNLØSN. UTTAK VP', 'DIVIDEND']:
                if sym not in detailed_flows: detailed_flows[sym] = []
                detailed_flows[sym].append((t_date_obj, amt))
                if t_type == 'DIVIDEND': dividends[sym] = dividends.get(sym, 0.0) + amt
                else: pos_flows[sym] = pos_flows.get(sym, 0.0) + amt

    # Cleanup tiny positions
    soy_holdings = {k: v for k, v in soy_holdings.items() if abs(v['qty']) > 0.001}
    eoy_holdings = {k: v for k, v in eoy_holdings.items() if abs(v['qty']) > 0.001}

    # Value Snapshots
    all_pos_syms = set(soy_holdings.keys()) | set(eoy_holdings.keys())
    fetch_list = list(all_pos_syms)
    fx_map = {}
    for sym in all_pos_syms:
        c = sym_currency.get(sym, 'NOK')
        if c != 'NOK':
            pair = f"{c}NOK=X"; fetch_list.append(pair); fx_map[c] = pair
    
    p_soy = get_historical_prices_by_date(fetch_list, soy_date)
    p_eoy = get_historical_prices_by_date(fetch_list, eoy_date)

    missing_prices = []

    def get_price_with_fallback(s, p_dict, ref_date):
        # 1. Try Yahoo
        p = p_dict.get(s, 0.0)
        if p > 0: return p
        
        # 2. Try Database (Nearest Transaction)
        conn = get_connection()
        
        # Handle FX Pairs (e.g. HKDNOK=X)
        if s.endswith("NOK=X"):
            curr = s.replace("NOK=X", "")
            query = """
                SELECT t.exchange_rate FROM transactions t
                JOIN instruments i ON t.instrument_id = i.id
                WHERE i.currency = ? AND t.exchange_rate > 0
                ORDER BY ABS(strftime('%J', t.date) - strftime('%J', ?))
                LIMIT 1
            """
            row = conn.execute(query, (curr, ref_date)).fetchone()
            conn.close()
            if row:
                missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'FX_FALLBACK', 'price': row[0]})
                return row[0]
            return 1.0 # Default to 1.0 if no FX history found # Default to 1.0 if no FX history found

        # Handle Standard Instruments
        query = """
            SELECT price FROM transactions t
            JOIN instruments i ON t.instrument_id = i.id
            WHERE i.symbol = ? AND t.price > 0 AND t.type IN ('BUY', 'SELL')
            ORDER BY ABS(strftime('%J', t.date) - strftime('%J', ?))
            LIMIT 1
        """
        row = conn.execute(query, (s, ref_date)).fetchone()
        conn.close()
        
        if row: 
            missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'DB_FALLBACK', 'price': row[0]})
            return row[0]
        
        missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'MISSING', 'price': 0.0})
        return 0.0

    def calc_snapshot_eq(h_dict, p_dict, cash_v, ref_date):
        total_v = 0.0
        for s, h in h_dict.items():
            if abs(h['qty']) < 0.001: continue
            p = get_price_with_fallback(s, p_dict, ref_date)
            curr = sym_currency.get(s, 'NOK'); r = 1.0
            if curr != 'NOK': 
                pair = fx_map.get(curr)
                r = get_price_with_fallback(pair, p_dict, ref_date)
            
            adj_q = get_adjusted_qty(s, h['qty'], ref_date, split_map)
            total_v += (adj_q * p * r) if p > 0 else h['cost']
        return total_v + cash_v

    eq_soy = calc_snapshot_eq(soy_holdings, p_soy, cash_soy, soy_date)
    eq_eoy = calc_snapshot_eq(eoy_holdings, p_eoy, cash_eoy, eoy_date)
    total_portfolio_profit = eq_eoy - eq_soy - cash_flows_ext
    
    # Portfolio XIRR
    x_flows = []
    if eq_soy > 0: x_flows.append((pd.Timestamp(soy_date), -eq_soy))
    x_flows.extend(yearly_detailed_flows.get(target_year, []))
    if eq_eoy > 0: x_flows.append((pd.Timestamp(eoy_date), eq_eoy))
    total_portfolio_xirr = xirr(x_flows) * 100

    # Build Result
    report = []; sum_pos_profit = 0.0
    for s in all_pos_syms:
        def get_v(h_d, p_d, ref_d):
            h = h_d.get(s, {'qty': 0.0, 'cost': 0.0})
            p = get_price_with_fallback(s, p_d, ref_d)
            curr = sym_currency.get(s, 'NOK'); r = 1.0
            if curr != 'NOK': 
                pair = fx_map.get(curr)
                r = get_price_with_fallback(pair, p_d, ref_d)
            aq = get_adjusted_qty(s, h['qty'], ref_d, split_map)
            return (aq * p * r) if p > 0 else h['cost']
        vs = get_v(soy_holdings, p_soy, soy_date); ve = get_v(eoy_holdings, p_eoy, eoy_date); nf = pos_flows.get(s, 0.0); dv = dividends.get(s, 0.0)
        profit = ve - vs + nf + dv; sum_pos_profit += profit
        i_x_flows = []
        if vs > 0: i_x_flows.append((pd.Timestamp(soy_date), -vs))
        i_x_flows.extend(detailed_flows.get(s, []))
        if ve > 0: i_x_flows.append((pd.Timestamp(eoy_date), ve))
        i_irr = xirr(i_x_flows) * 100
        if abs(vs) > 1 or abs(ve) > 1 or abs(profit) > 1:
            report.append({'Symbol': s, 'SOY Value': vs, 'EOY Value': ve, 'Net Additions': -nf, 'Dividends': dv, 'Profit': profit, 'IRR %': i_irr})

    float_profit = total_portfolio_profit - sum_pos_profit
    c_fx = float_profit - (fees_t + int_t + tax_t)
    if abs(fees_t) > 0.1: report.append({'Symbol': '[Fees]', 'SOY Value': 0, 'EOY Value': 0, 'Net Additions': 0, 'Dividends': 0, 'Profit': fees_t, 'IRR %': 0})
    if abs(int_t) > 0.1: report.append({'Symbol': '[Interest]', 'SOY Value': 0, 'EOY Value': 0, 'Net Additions': 0, 'Dividends': 0, 'Profit': int_t, 'IRR %': 0})
    if abs(tax_t) > 0.1: report.append({'Symbol': '[Div Tax]', 'SOY Value': 0, 'EOY Value': 0, 'Net Additions': 0, 'Dividends': 0, 'Profit': tax_t, 'IRR %': 0})
    report.append({'Symbol': '[Cash FX & Float]*', 'SOY Value': cash_soy, 'EOY Value': cash_eoy, 'Net Additions': cash_flows_ext, 'Dividends': 0, 'Profit': c_fx, 'IRR %': 0.0})
    df_res = pd.DataFrame(report)
    df_res['Contribution %'] = (df_res['Profit'] / total_portfolio_profit) * total_portfolio_xirr if abs(total_portfolio_profit) > 1 else 0.0
    return df_res.sort_values('Profit', ascending=False), total_portfolio_xirr, missing_prices

def get_yearly_equity_curve():
    conn = get_connection()
    df = pd.read_sql_query("SELECT t.date, t.type, t.instrument_id, t.quantity, t.amount_local, i.symbol, i.currency FROM transactions t LEFT JOIN instruments i ON t.instrument_id = i.id ORDER BY t.date, t.id", conn)
    conn.close()
    if df.empty: return pd.DataFrame()
    df['year'] = df['date'].str[:4]; years = sorted(df['year'].unique())
    split_map = get_internal_splits()
    holdings = {}; cash_balance = 0.0; results = []
    # 1. External Flows (Portfolio Level)
    flow_txns = df[df['type'].isin(['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT', 'OVERFØRING VIA TRUSTLY'])].copy()
    flow_txns['date_obj'] = pd.to_datetime(flow_txns['date'], format='mixed')
    y_flows = {}
    for _, row in flow_txns.iterrows():
        y = row['year']; d = row['date_obj']; amt = row['amount_local']
        if y not in y_flows: y_flows[y] = []
        y_flows[y].append((d, -amt))
    previous_equity = 0.0
    missing_prices = []

    def get_price_with_fallback(s, p_dict, ref_date):
        # 1. Try Yahoo
        p = p_dict.get(s, 0.0)
        if p > 0: return p
        
        # 2. Try Database (Nearest Transaction)
        conn = get_connection()
        
        # Handle FX Pairs (e.g. HKDNOK=X)
        if s.endswith("NOK=X"):
            curr = s.replace("NOK=X", "")
            query = """
                SELECT t.exchange_rate FROM transactions t
                JOIN instruments i ON t.instrument_id = i.id
                WHERE i.currency = ? AND t.exchange_rate > 0
                ORDER BY ABS(strftime('%J', t.date) - strftime('%J', ?))
                LIMIT 1
            """
            row = conn.execute(query, (curr, ref_date)).fetchone()
            conn.close()
            if row:
                missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'FX_FALLBACK', 'price': row[0]})
                return row[0]
            return 1.0 # Default to 1.0 if no FX history found

        query = """
            SELECT price FROM transactions t
            JOIN instruments i ON t.instrument_id = i.id
            WHERE i.symbol = ? AND t.price > 0 AND t.type IN ('BUY', 'SELL')
            ORDER BY ABS(strftime('%J', t.date) - strftime('%J', ?))
            LIMIT 1
        """
        row = conn.execute(query, (s, ref_date)).fetchone()
        conn.close()
        
        if row: 
            missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'DB_FALLBACK', 'price': row[0]})
            return row[0]
        
        missing_prices.append({'symbol': s, 'date': ref_date, 'type': 'MISSING', 'price': 0.0})
        return 0.0

    for year in years:
        for _, row in df[df['year'] == year].iterrows():
            t_type = row['type']; qty = row['quantity']; amt = row['amount_local']; cash_balance += amt; sym = row['symbol']
            if sym:
                if sym not in holdings: holdings[sym] = {'qty': 0.0, 'cost': 0.0, 'curr': row['currency']}
                h = holdings[sym]
                if t_type in INFLOW_TYPES: h['qty'] += qty; h['cost'] += abs(amt)
                elif t_type in OUTFLOW_TYPES:
                    if h['qty'] > 0: h['cost'] -= (h['cost'] / h['qty']) * abs(qty)
                    h['qty'] += qty
        to_remove = [k for k, v in holdings.items() if abs(v['qty']) < 0.001]
        for k in to_remove: del holdings[k]
        date_str = f"{year}-12-31"; fetch_list = list(holdings.keys())
        for s in list(holdings.keys()):
            if holdings[s]['curr'] != 'NOK':
                pair = f"{holdings[s]['curr']}NOK=X"
                if pair not in fetch_list: fetch_list.append(pair)
        price_data = get_historical_prices_by_date(fetch_list, date_str)
        equity_holdings = 0.0
        for s, h in holdings.items():
            price = get_price_with_fallback(s, price_data, date_str); rate = 1.0
            if h['curr'] != 'NOK': rate = price_data.get(f"{h['curr']}NOK=X", 1.0)
            aq = get_adjusted_qty(s, h['qty'], date_str, split_map)
            equity_holdings += (aq * price * rate) if price > 0 else h['cost']
        total_equity = equity_holdings + cash_balance
        x_flows = []
        if previous_equity > 0: x_flows.append((pd.Timestamp(f"{int(year)-1}-12-31"), -previous_equity))
        x_flows.extend(y_flows.get(year, []))
        if total_equity > 0: x_flows.append((pd.Timestamp(date_str), total_equity))
        results.append({'year': year, 'start_equity': previous_equity, 'net_flow': sum([-a for _, a in y_flows.get(year, [])]), 'end_equity': total_equity, 'profit': total_equity - previous_equity - sum([-a for _, a in y_flows.get(year, [])]), 'return_pct': xirr(x_flows) * 100})
        previous_equity = total_equity
    return pd.DataFrame(results), missing_prices

def get_holdings(date=None):
    conn = get_connection(); date_filter = ""; params = []
    if date: date_filter = "AND t.date <= ?"; params = [date]
    df = pd.read_sql(f"SELECT t.instrument_id, t.type, t.quantity, t.amount_local, t.date, i.symbol, i.isin FROM transactions t LEFT JOIN instruments i ON t.instrument_id = i.id WHERE t.instrument_id IS NOT NULL {date_filter} ORDER BY t.instrument_id, t.date", conn, params=params)
    conn.close()
    if df.empty: return pd.DataFrame()
    final_holdings = []
    for inst_id, group in df.groupby('instrument_id'):
        total_qty = 0.0; total_cost = 0.0; first_row = group.iloc[0]
        for _, row in group.iterrows():
            if any(t in row['type'] for t in INFLOW_TYPES): total_qty += row['quantity']; total_cost += abs(row['amount_local'])
            elif any(t in row['type'] for t in OUTFLOW_TYPES):
                if total_qty > 0: total_cost -= (total_cost / total_qty) * abs(row['quantity'])
                total_qty += row['quantity']
        if abs(total_qty) > 0.001: final_holdings.append({'instrument_id': inst_id, 'symbol': first_row['symbol'], 'isin': first_row['isin'], 'quantity': total_qty, 'cost_basis_local': max(0, total_cost)})
    return pd.DataFrame(final_holdings)

def get_income_and_costs():
    row = execute_query('''
        SELECT 
            SUM(CASE WHEN type = 'DIVIDEND' THEN amount_local ELSE 0 END) as dividends,
            SUM(CASE WHEN type = 'INTEREST' THEN ABS(amount_local) ELSE 0 END) as interest,
            SUM(CASE WHEN type = 'FEE' THEN ABS(amount_local) ELSE fee_local END) as fees
        FROM transactions
    ''')[0]
    return {'dividends': row['dividends'] or 0, 'interest': row['interest'] or 0, 'fees': row['fees'] or 0}

def get_total_xirr():
    conn = get_connection(); df = pd.read_sql_query("SELECT date, type, amount_local FROM transactions", conn); conn.close()
    if df.empty: return 0.0
    # 1. External Flows (Portfolio Level)
    flow_txns = df[df['type'].isin(['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT', 'OVERFØRING VIA TRUSTLY'])].copy()
    flow_txns['date_obj'] = pd.to_datetime(flow_txns['date'], format='mixed')
    x_flows = [(row['date_obj'], -row['amount_local']) for _, row in flow_txns.iterrows()]
    df_h = get_holdings()
    total_mv = 0.0
    if not df_h.empty:
        from scripts.shared.market_data import get_latest_prices, get_exchange_rate
        prices = get_latest_prices(df_h['instrument_id'].tolist())
        for _, r in df_h.iterrows():
            m = prices.get(r['instrument_id'])
            if m:
                p, c = m; fx = get_exchange_rate(c, 'NOK') if c != 'NOK' else 1.0
                total_mv += r['quantity'] * p * fx
            else: total_mv += r['cost_basis_local']
    curr_eq = total_mv + df['amount_local'].sum()
    if curr_eq > 0: x_flows.append((pd.Timestamp.now(), curr_eq))
    return xirr(x_flows) * 100

def get_dividend_details():
    """
    Returns detailed dividend data:
    1. Yearly totals
    2. Top payers (Current Year - 2025)
    3. Top payers (All Time)
    """
    conn = get_connection()

    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT
            strftime('%Y', date) as year,
            SUM(amount_local) as total
        FROM transactions
        WHERE type = 'DIVIDEND'
        GROUP BY year
        ORDER BY year
    """, conn)

    # 2. By Ticker (2025)
    df_current_year = pd.read_sql_query("""
        SELECT
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND' AND t.date LIKE '2025%'
        GROUP BY symbol
        ORDER BY total DESC
    """, conn)

    # 3. By Ticker (All Time)
    df_all_time = pd.read_sql_query("""
        SELECT
            COALESCE(i.symbol, i.isin) as symbol,
            SUM(t.amount_local) as total
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        WHERE t.type = 'DIVIDEND'
        GROUP BY symbol
        ORDER BY total DESC
    """, conn)

    conn.close()
    return df_yearly, df_current_year, df_all_time

def get_interest_details():
    """
    Returns detailed interest data:
    1. Yearly totals
    2. By Currency
    3. Top Payments
    """
    conn = get_connection()

    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT
            strftime('%Y', date) as year,
            SUM(ABS(amount_local)) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY year
        ORDER BY year
    """, conn)

    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT
            currency,
            SUM(ABS(amount_local)) as total
        FROM transactions
        WHERE type = 'INTEREST'
        GROUP BY currency
        ORDER BY total DESC
    """, conn)

    # 3. Recent Payments
    df_top = pd.read_sql_query("""
        SELECT
            date,
            currency,
            ABS(amount) as amount,
            ABS(amount_local) as amount_local,
            source_file
        FROM transactions
        WHERE type = 'INTEREST'
        ORDER BY date DESC
        LIMIT 50
    """, conn)

    conn.close()
    return df_yearly, df_currency, df_top

def get_fee_details():
    """
    Returns detailed fee data:
    1. Yearly totals
    2. By Currency
    3. Top Payments
    """
    conn = get_connection()

    # 1. Yearly
    df_yearly = pd.read_sql_query("""
        SELECT
            strftime('%Y', date) as year,
            SUM(
                CASE
                    WHEN type = 'FEE' THEN ABS(amount_local)
                    ELSE fee_local
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY year
        ORDER BY year
    """, conn)

    # 2. By Currency
    df_currency = pd.read_sql_query("""
        SELECT
            currency,
            SUM(
                CASE
                    WHEN type = 'FEE' THEN ABS(amount_local)
                    ELSE fee_local
                END
            ) as total
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        GROUP BY currency
        ORDER BY total DESC
    """, conn)

    # 3. Recent Fees
    df_top = pd.read_sql_query("""
        SELECT
            date,
            currency,
            CASE
                WHEN type = 'FEE' THEN ABS(amount_local)
                ELSE fee_local
            END as amount_local,
            source_file
        FROM transactions
        WHERE type = 'FEE' OR fee_local > 0
        ORDER BY date DESC
        LIMIT 50
    """, conn)

    conn.close()
    return df_yearly, df_currency, df_top

def get_fx_performance():
    """
    Calculates Realized P&L, Remaining Holdings, and Cost Basis for FX trades.
    Returns a DataFrame.
    """
    conn = get_connection()

    # Fetch all FX transactions for non-NOK currencies
    query = """
        SELECT
            date,
            currency,
            amount as quantity,
            amount_local
        FROM transactions
        WHERE type = 'CURRENCY_EXCHANGE'
          AND currency != 'NOK'
        ORDER BY date, id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    results = []

    # Process each currency
    for currency, group in df.groupby('currency'):
        holdings = 0.0
        total_cost = 0.0
        realized_pl = 0.0

        # Sort just in case
        group = group.sort_values('date')

        for _, row in group.iterrows():
            qty = row['quantity']
            val_nok = row['amount_local']

            if qty > 0:
                # BUY (Inflow of Foreign Currency)
                holdings += qty
                total_cost += val_nok

            elif qty < 0:
                # SELL (Outflow of Foreign Currency)
                if holdings <= 0:
                    cost_portion = 0
                else:
                    portion = abs(qty) / holdings
                    portion = min(portion, 1.0)
                    cost_portion = total_cost * portion

                proceeds = abs(val_nok)
                gain = proceeds - cost_portion
                realized_pl += gain

                # Update Inventory
                holdings += qty
                total_cost -= cost_portion

                if abs(holdings) < 0.01:
                    holdings = 0
                    total_cost = 0

        results.append({
            'currency': currency,
            'realized_pl_nok': realized_pl,
            'holdings': holdings,
            'cost_basis_nok': total_cost
        })

    return pd.DataFrame(results)

def get_realized_performance():
    """
    Replays the ledger to calculate Realized Gains, Dividends, Fees, etc. by Year.
    Returns a DataFrame: year | realized_gl | dividends | interest | fees | tax | total_pl
    """
    conn = get_connection()

    # Get all transactions sorted by date
    query = '''
        SELECT
            t.date, t.type, t.instrument_id, t.quantity, t.amount_local,
            t.fee_local, i.symbol
        FROM transactions t
        LEFT JOIN instruments i ON t.instrument_id = i.id
        ORDER BY t.date, t.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    # State
    holdings = {} # inst_id -> {qty, total_cost}
    yearly = {}   # year -> {realized_gl, dividends, interest, fees, tax}

    def get_year(date_str):
        return str(date_str)[:4]

    def add_stat(year, category, value):
        if year not in yearly:
            yearly[year] = {'realized_gl': 0.0, 'dividends': 0.0, 'interest': 0.0, 'fees': 0.0, 'tax': 0.0}
        yearly[year][category] += value

    # Replay
    for _, row in df.iterrows():
        year = get_year(row['date'])
        t_type = row['type']
        inst_id = row['instrument_id']
        qty = row['quantity']
        amt = row['amount_local']
        fee = row['fee_local'] if pd.notna(row['fee_local']) else 0.0

        # Always track fees
        if fee > 0:
            add_stat(year, 'fees', -abs(fee)) # fees are negative impact

        # 1. Income / Costs
        if t_type == 'DIVIDEND':
            add_stat(year, 'dividends', amt)
        elif t_type == 'INTEREST':
            add_stat(year, 'interest', amt) # usually negative
        elif t_type == 'TAX':
            add_stat(year, 'tax', amt)      # usually negative
        elif t_type == 'FEE':
            add_stat(year, 'fees', -abs(amt)) # Explicit fee transaction

        # 2. Capital Gains (Buy/Sell)
        # Only process if instrument is involved
        if inst_id:
            if inst_id not in holdings:
                holdings[inst_id] = {'qty': 0.0, 'cost': 0.0}

            h = holdings[inst_id]

            # Identify Buy vs Sell using logic similar to get_holdings
            
            # INFLOW (Buy)
            if t_type in ['BUY', 'DEPOSIT', 'TRANSFER_IN', 'TILDELING INNLEGG RE', 'BYTTE INNLEGG VP', 'EMISJON INNLEGG VP']:
                # Add to inventory
                h['qty'] += qty
                # Cost increases by amount paid (usually negative amount, so we take abs)
                cost_added = abs(amt)
                h['cost'] += cost_added

            # OUTFLOW (Sell)
            elif t_type in ['SELL', 'WITHDRAWAL', 'TRANSFER_OUT', 'INNLØSN. UTTAK VP', 'BYTTE UTTAK VP']:
                # Calculate Realized Gain
                # Avg Cost Basis
                if h['qty'] > 0:
                    avg_cost = h['cost'] / h['qty']
                    cost_of_sold = avg_cost * abs(qty)

                    # Proceeds = Amount received (positive for sell)
                    proceeds = abs(amt)

                    # Gain = Proceeds - Cost
                    if t_type in ['SELL', 'INNLØSN. UTTAK VP', 'BYTTE UTTAK VP']:
                        gain = proceeds - cost_of_sold
                        add_stat(year, 'realized_gl', gain)

                    # Reduce Inventory
                    h['cost'] -= cost_of_sold

                h['qty'] += qty # qty is negative

                # Cleanup dust
                if abs(h['qty']) < 0.001:
                    h['qty'] = 0.0
                    h['cost'] = 0.0

    # Convert to DataFrame
    data = []
    for year, stats in yearly.items():
        row = stats.copy()
        row['year'] = year
        row['total_pl'] = sum(stats.values())
        data.append(row)

    if not data:
        return pd.DataFrame()
        
    return pd.DataFrame(data).sort_values('year')
