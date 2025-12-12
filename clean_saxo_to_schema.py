import pandas as pd
import os
import re
import uuid
import numpy as np

def clean_saxo_transactions_to_schema(input_file_path, output_file_path):
    print(f"Processing '{os.path.basename(input_file_path)}' with final logic...")
    
    df = pd.read_excel(input_file_path, sheet_name='Transaksjoner')

    column_mapping = {
        'Kunde-ID': 'AccountID',
        'Handelsdato': 'TradeDate',
        'Valuteringsdato': 'SettlementDate',
        'Instrument ISIN': 'ISIN',
        'Instrument': 'Symbol',
        'Type': 'SaxoTransactionType',
        'Hendelse': 'SaxoEventText',
        'Bokført beløp': 'Amount_Base_Raw', # This is always NOK
        'Omregningskurs': 'ExchangeRate'
    }
    df = df.rename(columns=column_mapping)
    
    df = df.dropna(subset=['AccountID', 'TradeDate']).copy()
    df['Source'] = 'SAXO'

    df['TradeDate'] = pd.to_datetime(df['TradeDate'], errors='coerce')
    df['SettlementDate'] = pd.to_datetime(df['SettlementDate'], errors='coerce')
    df['Amount_Base_Raw'] = pd.to_numeric(df['Amount_Base_Raw'], errors='coerce').fillna(0)
    df['ExchangeRate'] = pd.to_numeric(df['ExchangeRate'], errors='coerce').fillna(1.0)

    trade_pattern = re.compile(r"(?P<action>Kjøp|Salg|Selg)\s+(?P<quantity>[-]?[\d,.]+)\s+@\s+(?P<price>[\d,.]+)\s+(?P<currency>\w+)", re.IGNORECASE)

    processed_rows = []
    for index, row in df.iterrows():
        output_row = {
            'GlobalID': str(uuid.uuid4()), 'Source': 'SAXO', 'AccountID': row['AccountID'],
            'OriginalID': None, 'ParentID': None, 'TradeDate': row['TradeDate'], 
            'SettlementDate': row['SettlementDate'], 'Symbol': row['Symbol'], 'ISIN': row['ISIN'],
            'Description': str(row['SaxoEventText']), 'Quantity': 0.0, 'Price': 0.0,
            'Amount_Base': row['Amount_Base_Raw'], 'Currency_Base': 'NOK',
            'Amount_Local': np.nan, 'Currency_Local': np.nan, 'ExchangeRate': row['ExchangeRate']
        }

        text = str(row['SaxoEventText'])
        trade_match = trade_pattern.search(text)

        if trade_match:
            data = trade_match.groupdict()
            action = data['action'].lower()
            quantity_from_text = float(data['quantity'].replace(',', ''))
            price = float(data['price'].replace(',', ''))
            currency = data['currency'].upper()

            output_row['Price'] = price
            output_row['Currency_Local'] = currency
            
            # Always work with the absolute quantity for calculation, and sign it based on the action
            abs_quantity = abs(quantity_from_text)
            
            pure_value_local = abs_quantity * price
            pure_value_base = pure_value_local * row['ExchangeRate']
            total_value_base = abs(row['Amount_Base_Raw'])
            fee_base = total_value_base - pure_value_base

            if action in ['kjøp', 'buy']:
                output_row['Type'] = 'BUY'
                output_row['Quantity'] = abs_quantity
                output_row['Amount_Local'] = -pure_value_local
                output_row['Amount_Base'] = -pure_value_base
            elif action in ['salg', 'selg']:
                output_row['Type'] = 'SELL'
                output_row['Quantity'] = -abs_quantity
                output_row['Amount_Local'] = pure_value_local
                output_row['Amount_Base'] = pure_value_base
            
            processed_rows.append(output_row)

            if fee_base > 1e-4:
                fee_row = output_row.copy()
                fee_row['GlobalID'], fee_row['ParentID'], fee_row['Type'] = str(uuid.uuid4()), output_row['GlobalID'], 'FEE'
                fee_row['Quantity'], fee_row['Price'] = 0, 0
                fee_row['Amount_Base'] = -fee_base
                fee_row['Amount_Local'] = -fee_base / row['ExchangeRate'] if row['ExchangeRate'] != 0 else -fee_base
                fee_row['Description'] = f"Fee for trade {output_row['GlobalID']}"
                processed_rows.append(fee_row)
        else:
            # Handle Non-Trade Events
            saxo_type_text = str(row['SaxoTransactionType']).lower()
            event_text = str(row['SaxoEventText']).lower()
            
            if 'utbytte' in event_text or 'dividend' in event_text: output_row['Type'] = 'DIVIDEND'
            elif 'depotgebyr' in event_text or 'custody fee' in event_text: output_row['Type'] = 'FEE'
            elif 'gebyr' in saxo_type_text or 'fee' in saxo_type_text: output_row['Type'] = 'FEE'
            elif 'rente' in event_text or 'interest' in event_text: output_row['Type'] = 'INTEREST'
            elif 'innskudd' in event_text or 'deposit' in event_text: output_row['Type'] = 'DEPOSIT'
            elif 'uttak' in event_text or 'withdrawal' in event_text: output_row['Type'] = 'WITHDRAWAL'
            else: output_row['Type'] = 'ADJUSTMENT'
            
            # Sign amounts for non-trade events
            if output_row['Type'] in ['FEE', 'WITHDRAWAL']:
                output_row['Amount_Base'] = -abs(row['Amount_Base_Raw'])
            else: # DIVIDEND, INTEREST, DEPOSIT, ADJUSTMENT (assume positive unless specified)
                output_row['Amount_Base'] = abs(row['Amount_Base_Raw'])

            # FX rate logic for non-trade events
            currency_match = re.search(r'b(USD|EUR|SEK|DKK|CAD|GBP|CHF|JPY|AUD|CNY|HKD|NOK)b', event_text, re.IGNORECASE)
            
            # Default to NOK transaction if no currency is found or if currency is NOK
            if not currency_match or currency_match.group(0).upper() == 'NOK':
                output_row['Amount_Local'] = output_row['Amount_Base']
                output_row['Currency_Local'] = 'NOK'
                output_row['ExchangeRate'] = 1.0
            else:
                # It's a foreign currency event.
                output_row['Currency_Local'] = currency_match.group(0).upper()
                exchange_rate = row['ExchangeRate'] if row['ExchangeRate'] != 0 else 1.0
                output_row['ExchangeRate'] = exchange_rate
                output_row['Amount_Local'] = output_row['Amount_Base'] / exchange_rate

            processed_rows.append(output_row)

    df_out = pd.DataFrame(processed_rows)
    final_columns = [
        'GlobalID', 'Source', 'AccountID', 'OriginalID', 'ParentID',
        'TradeDate', 'SettlementDate', 'Type', 'Symbol', 'ISIN',
        'Description', 'Quantity', 'Price', 
        'Amount_Base', 'Currency_Base', 
        'Amount_Local', 'Currency_Local', 
        'ExchangeRate'
    ]
    df_out = df_out[final_columns]
    df_out.to_excel(output_file_path, index=False)
    print(f"\nCleaned SAXO transaction data saved to {output_file_path}")
    print("\n--- First 15 rows of final cleaned SAXO transaction data ---")
    print(df_out.head(15).to_markdown(index=False))

if __name__ == "__main__":
    saxo_transactions_file = {
        'input_file': r"C:\Users\Samir\project-kodak\data\Transactions_19269921_2024-11-07_2025-12-11.xlsx",
        'output_file': 'saxo_transactions_schema.xlsx'
    }
    clean_saxo_transactions_to_schema(saxo_transactions_file['input_file'], saxo_transactions_file['output_file'])
