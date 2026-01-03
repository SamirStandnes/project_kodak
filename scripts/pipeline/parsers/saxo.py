import pandas as pd
import uuid
import os
import re
from typing import List, Dict, Any
from scripts.shared.utils import clean_num, load_config

# --- Configuration ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

def parse(file_path: str) -> List[Dict[str, Any]]:
    try:
        xl = pd.ExcelFile(file_path)
        sheet = 'Transactions' if 'Transactions' in xl.sheet_names else 'Transaksjoner'
        df = pd.read_excel(xl, sheet_name=sheet)
        xl.close()
    except Exception as e:
        print(f'Error reading Saxo file {file_path}: {e}')
        return []
        
    col_map = {
        'Kunde-ID': 'AccountID', 'Client ID': 'AccountID',
        'Handelsdato': 'TradeDate', 'Trade Date': 'TradeDate',
        'Valuteringsdato': 'SettlementDate', 'Value Date': 'SettlementDate',
        'Instrument ISIN': 'ISIN',
        'Instrumentsymbol': 'Symbol', 'Instrument Symbol': 'Symbol',
        'Hendelse': 'Event', 'Event': 'Event',
        'Bokført beløp': 'Amount', 'Booked Amount': 'Amount',
        'Omregningskurs': 'FXRate', 'Conversion Rate': 'FXRate',
        'Type': 'SaxoType'
    }

    existing_cols = {c: col_map[c] for c in df.columns if c in col_map}
    df = df.rename(columns=existing_cols)
    
    if 'Symbol' not in df.columns and 'Instrument' in df.columns:
        df = df.rename(columns={'Instrument': 'Symbol'})

    df = df.dropna(subset=['AccountID', 'TradeDate'])
    
    trade_pattern = re.compile(r'(?P<action>Kjøp|Salg|Selg|Buy|Sell)\s+(?P<quantity>[-]?[\d,. ]+)\s+@\s+(?P<price>[\d,. ]+)\s+(?P<currency>\w+)', re.IGNORECASE)

    results = []
    
    for _, row in df.iterrows():
        text = str(row['Event'])
        match = trade_pattern.search(text)
        
        amt_local = clean_num(row['Amount'])
        fx_rate = clean_num(row['FXRate']) if 'FXRate' in row and pd.notna(row['FXRate']) else 1.0
        
        item = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': str(row['AccountID']),
            'isin': row['ISIN'] if 'ISIN' in row else None,
            'symbol': row['Symbol'] if 'Symbol' in row else None,
            'date': row['TradeDate'],
            'type': 'OTHER',
            'quantity': 0.0,
            'price': 0.0,
            'amount': amt_local,
            'currency': BASE_CURRENCY,
            'amount_local': amt_local,
            'exchange_rate': fx_rate,
            'description': text,
            'source_file': os.path.basename(file_path),
            'fee': 0.0,
            'fee_currency': BASE_CURRENCY,
            'fee_local': 0.0
        }
        
        if match:
            data = match.groupdict()
            action = data['action'].lower()
            qty = float(data['quantity'].replace(',', '').replace(' ', ''))
            price = float(data['price'].replace(',', '').replace(' ', ''))
            raw_curr = data['currency'].upper()
            
            item['price'] = price
            item['currency'] = raw_curr
            
            # Recalculate raw amount if we have a valid rate
            if fx_rate > 0 and fx_rate != 1.0:
                item['amount'] = amt_local / fx_rate
            
            if action in ['kjøp', 'buy']:
                item['type'] = 'BUY'
                item['quantity'] = abs(qty)
            else:
                item['type'] = 'SELL'
                item['quantity'] = -abs(qty)

        else:
            saxo_type = str(row['SaxoType']).lower() if 'SaxoType' in row else ''
            if 'utbytte' in text.lower() or 'dividend' in text.lower(): item['type'] = 'DIVIDEND'
            elif 'innskudd' in text.lower() or 'deposit' in text.lower(): item['type'] = 'DEPOSIT'
            elif 'uttak' in text.lower() or 'withdrawal' in text.lower(): item['type'] = 'WITHDRAWAL'
            elif 'gebyr' in text.lower() or 'fee' in text.lower(): item['type'] = 'FEE'
            elif 'interest' in text.lower(): item['type'] = 'INTEREST'
            else: item['type'] = 'ADJUSTMENT'

        results.append(item)
        
    return results
