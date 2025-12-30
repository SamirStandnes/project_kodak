import pandas as pd
import numpy as np
import uuid
import os
import re
from typing import List, Dict, Any
from scripts.shared.utils import clean_num

# --- Nordnet Parser ---

def parse_nordnet(file_path: str) -> List[Dict[str, Any]]:
    try:
        df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
    except Exception as e:
        print(f'Error reading Nordnet file {file_path}: {e}')
        return []

    # Clean columns
    df['Beløp_Clean'] = df['Beløp'].apply(clean_num)
    df['Kurtasje_Clean'] = df['Kurtasje'].apply(clean_num)
    df['Kjøpsverdi_Clean'] = df['Kjøpsverdi'].apply(clean_num)
    df['Kurs_Clean'] = df['Kurs'].apply(clean_num)
    df['Antall_Clean'] = df['Antall'].apply(clean_num)

    results = []
    
    for _, row in df.iterrows():
        # 1. Classification
        t_type = str(row['Transaksjonstype']).upper()
        text = str(row['Transaksjonstekst']).upper() if pd.notna(row['Transaksjonstekst']) else ''
        
        std_type = t_type
        if 'INTERNAL' in text:
            if 'INNSKUDD' in t_type: std_type = 'TRANSFER_IN'
            elif 'UTTAK' in t_type: std_type = 'TRANSFER_OUT'
        elif 'OVERFØRING' in t_type and 'INNSKUD' in t_type: std_type = 'DEPOSIT'
        elif 'ÖNSKAR TECKNA' in text: std_type = 'ADJUSTMENT'
        else:
            mapping = {
                'KJØPT': 'BUY', 'SALG': 'SELL', 'UTBYTTE': 'DIVIDEND',
                'INNSKUDD': 'DEPOSIT', 'UTTAK': 'WITHDRAWAL', 'UTTAK INTERNET': 'WITHDRAWAL',
                'DEBETRENTE': 'INTEREST', 'INNLØSN. UTTAK VP': 'SELL', 
                'AVG KORR': 'ADJUSTMENT', 'ERSTATNING': 'DEPOSIT',
                'SALG VALUTA': 'CURRENCY_EXCHANGE', 'KJØP VALUTA': 'CURRENCY_EXCHANGE', 
                'AVGIFT': 'FEE', 'PLATTFORMAVGIFT': 'FEE'
            }
            if t_type in mapping: std_type = mapping[t_type]
            elif 'RENTE' in t_type: std_type = 'INTEREST'
            elif 'SKATT' in t_type: std_type = 'TAX'

        # 2. Correct Column Swapping
        v1 = row['Valuta.1'] if pd.notna(row['Valuta.1']) else 'NOK'
        v2 = row['Valuta.2'] if pd.notna(row['Valuta.2']) else 'NOK'
        a1 = row['Beløp_Clean']
        a2 = row['Kjøpsverdi_Clean']
        
        if v1 == 'NOK' and v2 != 'NOK':
            # Auto-FX: Settled in NOK
            amount_local = a1
            amount = a1 # Use NOK amount as the main amount
            currency = 'NOK' # Record as NOK transaction
            # Note: We lose the foreign amount in the 'amount' field, 
            # but we can preserve it in notes or rely on instrument currency.
        elif v1 != 'NOK' and v2 == 'NOK':
            amount = a1
            currency = v1
            amount_local = a2
        else:
            amount = a1
            currency = v1
            amount_local = a2 if a2 != 0 else a1

        # 3. Sign Logic
        # For FX (CURRENCY_EXCHANGE) and INTEREST/FEE/TAX, we TRUST the signs from the file.
        # For others, we enforce consistency.
        if std_type not in ['CURRENCY_EXCHANGE', 'INTEREST', 'FEE', 'TAX']:
            outflow_types = ['BUY', 'WITHDRAWAL', 'TRANSFER_OUT']
            inflow_types = ['SELL', 'DEPOSIT', 'TRANSFER_IN', 'DIVIDEND']
            
            if std_type in outflow_types:
                amount_local = -abs(amount_local)
                amount = -abs(amount)
            elif std_type in inflow_types:
                amount_local = abs(amount_local)
                amount = abs(amount)

        # Quantity logic
        qty = row['Antall_Clean']
        if std_type == 'SELL' or 'UTTAK' in t_type:
            qty = -abs(qty)
        else:
            qty = abs(qty)

        exchange_rate = clean_num(row['Vekslingskurs'])
        if currency != 'NOK' and (pd.isna(row['Vekslingskurs']) or exchange_rate == 0):
             exchange_rate = 0.0 # Flag for enrichment

        # Fix for zero amount_local if rate exists
        if amount_local == 0 and amount != 0 and exchange_rate != 0:
            amount_local = amount * exchange_rate

        item = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': str(row['Portefølje']),
            'isin': row['ISIN'],
            'symbol': row['Verdipapir'],
            'date': row['Handelsdag'],
            'type': std_type,
            'quantity': qty,
            'price': row['Kurs_Clean'],
            'amount': amount,
            'currency': currency,
            'amount_local': amount_local,
            'exchange_rate': exchange_rate,
            'description': text,
            'source_file': os.path.basename(file_path),
            'fee': clean_num(row['Kurtasje_Clean'])
        }
        results.append(item)
        
    return results

# --- Saxo Parser ---

def parse_saxo(file_path: str) -> List[Dict[str, Any]]:
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
        
        amt_booked = clean_num(row['Amount'])
        
        item = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': str(row['AccountID']),
            'isin': row['ISIN'] if 'ISIN' in row else None,
            'symbol': row['Symbol'] if 'Symbol' in row else None,
            'date': row['TradeDate'],
            'type': 'OTHER',
            'quantity': 0.0,
            'price': 0.0,
            'amount': amt_booked,
            'currency': 'NOK',
            'amount_local': amt_booked,
            'exchange_rate': clean_num(row['FXRate']) if 'FXRate' in row else 1.0,
            'description': text,
            'source_file': os.path.basename(file_path),
            'fee': 0.0
        }
        
        if match:
            data = match.groupdict()
            action = data['action'].lower()
            qty = float(data['quantity'].replace(',', '').replace(' ', ''))
            price = float(data['price'].replace(',', '').replace(' ', ''))
            # We keep the currency for information in description if needed, 
            # but for Saxo, cash impact is always NOK
            item['price'] = price
            
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

        # Saxo specific: All cash impacts are settled in NOK
        item['currency'] = 'NOK'
        item['amount'] = item['amount_local']

        results.append(item)
        
    return results