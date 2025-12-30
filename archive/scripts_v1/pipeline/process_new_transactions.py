import pandas as pd
import sqlite3
import os
import uuid
from datetime import datetime
import re
import numpy as np
import glob
import hashlib
import logging

# --- Setup Logging ---
def setup_logging(batch_id):
    log_dir = os.path.join('data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"import_log_{batch_id}.txt")
    
    # Configure logging to write to file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

# --- Helper: Generate Transaction Hash ---
def _generate_txn_hash(row):
    """Generates a hash based on key transaction fields to identify duplicates."""
    date = str(row['TradeDate']).split(' ')[0] # YYYY-MM-DD
    acct = str(row['AccountID'])
    t_type = str(row['Type'])
    symbol = str(row['Symbol']) if row['Symbol'] and pd.notna(row['Symbol']) else ''
    amount = f"{float(row['Amount_Base']):.2f}" if pd.notna(row['Amount_Base']) else '0.00'
    
    raw_str = f"{date}|{acct}|{t_type}|{symbol}|{amount}"
    return hashlib.md5(raw_str.encode()).hexdigest()

# --- Helper: Clean Currency Strings ---
def _clean_num(val):
    if pd.isna(val) or val == '':
        return 0.0
    if isinstance(val, (float, int)):
        return float(val)
    val = str(val).replace(' ', '').replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0.0

# --- Cleaning Functions ---
def _clean_nordnet_data(input_file_path):
    logging.info(f"Parsing Nordnet file: {os.path.basename(input_file_path)}")
    try:
        df = pd.read_csv(input_file_path, sep='\t', encoding='utf-16')
    except Exception as e:
        logging.error(f"Failed to read file {input_file_path}: {e}")
        return pd.DataFrame()

    df['Beløp_Clean'] = df['Beløp'].apply(_clean_num)
    df['Kurtasje_Clean'] = df['Kurtasje'].apply(_clean_num)
    df['Kjøpsverdi_Clean'] = df['Kjøpsverdi'].apply(_clean_num)
    df['Kurs_Clean'] = df['Kurs'].apply(_clean_num)
    df['Antall_Clean'] = df['Antall'].apply(_clean_num)

    def classify_type(row):
        t_type = str(row['Transaksjonstype']).upper()
        text = str(row['Transaksjonstekst']).upper()
        
        if 'INTERNAL' in text:
            if 'INNSKUDD' in t_type: return 'TRANSFER_IN'
            if 'UTTAK' in t_type: return 'TRANSFER_OUT'
        if 'OVERFØRING' in t_type and 'INNSKUD' in t_type: return 'DEPOSIT'
        if 'ÖNSKAR TECKNA' in text: return 'ADJUSTMENT'
                
        mapping = {
            'KJØPT': 'BUY', 'SALG': 'SELL', 'UTBYTTE': 'DIVIDEND',
            'INNSKUDD': 'DEPOSIT', 'UTTAK': 'WITHDRAWAL', 'UTTAK INTERNET': 'WITHDRAWAL',
            'DEBETRENTE': 'INTEREST', 'INNLØSN. UTTAK VP': 'SELL', 'TILDELING INNLEGG RE': 'DEPOSIT',
            'AVG KORR': 'ADJUSTMENT', 'TILBAKEBET. FOND AVG': 'DEPOSIT', 'ERSTATNING': 'DEPOSIT',
            'SLETTING UTTAK VP': 'ADJUSTMENT', 'EMISJON INNLEGG VP': 'DEPOSIT', 'BYTTE INNLEGG VP': 'ADJUSTMENT',
            'BYTTE UTTAK VP': 'ADJUSTMENT', 'OVERFØRING VIA TRUSTLY': 'DEPOSIT', 'SALG VALUTA': 'CURRENCY_EXCHANGE',
            'KJØP VALUTA': 'CURRENCY_EXCHANGE', 'INNSKUDD KONTANTER': 'DEPOSIT', 'AVGIFT': 'FEE',
            'PLATTFORMAVGIFT': 'FEE', 'UTSKILLING FISJON IN': 'DEPOSIT'
        }
        if t_type in mapping: return mapping[t_type]
        if 'RENTE' in t_type: return 'INTEREST'
        if 'SKATT' in t_type: return 'TAX'
        return t_type

    df['StandardizedType'] = df.apply(classify_type, axis=1)

    processed_rows = []
    for index, row in df.iterrows():
        base_id = row['Id']
        source = 'Nordnet'
        account_id = row['Portefølje']
        trade_date = row['Handelsdag']
        settle_date = row['Oppgjørsdag']
        symbol = row['Verdipapir']
        isin = row['ISIN']
        description = row['Transaksjonstekst'] if pd.notna(row['Transaksjonstekst']) else symbol
        
        amount_base = row['Beløp_Clean']
        curr_base = row['Valuta.1'] if pd.notna(row['Valuta.1']) else 'NOK'
        
        amount_local = row['Kjøpsverdi_Clean']
        curr_local = row['Valuta.2']
        
        if pd.isna(curr_local):
            if pd.notna(row['Valuta']) and pd.notna(row['ISIN']):
                 curr_local = row['Valuta']
                 if amount_local == 0 and row['Antall_Clean'] != 0:
                     amount_local = row['Kurs_Clean'] * row['Antall_Clean']
            else:
                 curr_local = curr_base
                 if amount_local == 0:
                     amount_local = abs(amount_base)

        price = row['Kurs_Clean']
        t_type_upper = str(row['Transaksjonstype']).upper()

        if t_type_upper == 'BYTTE UTTAK VP': qty = -1 * abs(row['Antall_Clean'])
        elif t_type_upper == 'BYTTE INNLEGG VP': qty = abs(row['Antall_Clean'])
        elif row['StandardizedType'] in ['DIVIDEND', 'TAX', 'INTEREST', 'FEE', 'CURRENCY_EXCHANGE']: qty = 0
        elif row['StandardizedType'] == 'SELL': qty = -1 * abs(row['Antall_Clean'])
        elif row['StandardizedType'] == 'BUY': qty = abs(row['Antall_Clean'])
        else: qty = row['Antall_Clean']
        
        fee_val = row['Kurtasje_Clean']
        has_fee = (fee_val != 0 and not pd.isna(fee_val))
        
        main_row = {
            'GlobalID': str(uuid.uuid4()), 'Source': source, 'AccountID': account_id,
            'OriginalID': base_id, 'ParentID': None, 'TradeDate': trade_date, 
            'SettlementDate': settle_date, 'Type': row['StandardizedType'], 'Symbol': symbol, 'ISIN': isin,
            'Description': description, 'Quantity': qty, 'Price': price, 
            'Amount_Base': amount_base, 'Currency_Base': curr_base,
            'Amount_Local': amount_local, 'Currency_Local': curr_local, 'ExchangeRate': row['Vekslingskurs'],
            'SourceFile': os.path.basename(input_file_path),
            'SourceLine': index + 2 # +2 for header and 0-index
        }
        
        if has_fee:
            fee_amount_base = -1 * abs(fee_val)
            fee_row = main_row.copy()
            fee_row['GlobalID'], fee_row['ParentID'], fee_row['Type'] = str(uuid.uuid4()), main_row['GlobalID'], 'FEE'
            fee_row['Quantity'], fee_row['Price'] = 0, 0
            fee_row['Amount_Base'] = fee_amount_base
            fee_row['Description'] = f"Fee for txn {base_id}"
            fee_row['Currency_Base'] = row['Valuta'] if pd.notna(row['Valuta']) else curr_base
            fee_row['Amount_Local'], fee_row['Currency_Local'], fee_row['ExchangeRate'] = np.nan, np.nan, np.nan
            
            main_row['Amount_Base'] = main_row['Amount_Base'] - fee_amount_base

            exchange_rate = _clean_num(row['Vekslingskurs'])
            if curr_base != curr_local and exchange_rate != 0 and main_row['Amount_Local'] != 0:
                fee_in_local_currency = abs(fee_val) / exchange_rate
                main_row['Amount_Local'] = main_row['Amount_Local'] - fee_in_local_currency
            
            processed_rows.append(main_row)
            processed_rows.append(fee_row)
        else:
            processed_rows.append(main_row)

    return pd.DataFrame(processed_rows)

def _clean_saxo_data(input_file_path):
    logging.info(f"Parsing Saxo file: {os.path.basename(input_file_path)}")
    try:
        df = pd.read_excel(input_file_path, sheet_name='Transaksjoner')
    except Exception as e:
        logging.error(f"Failed to read file {input_file_path}: {e}")
        return pd.DataFrame()

    mapping_no = {
        'Kunde-ID': 'AccountID', 'Handelsdato': 'TradeDate', 'Valuteringsdato': 'SettlementDate',
        'Instrument ISIN': 'ISIN', 'Instrument': 'Symbol', 'Type': 'SaxoTransactionType',
        'Hendelse': 'SaxoEventText', 'Bokført beløp': 'Amount_Base_Raw', 'Omregningskurs': 'ExchangeRate'
    }
    mapping_en = {
        'Client ID': 'AccountID', 'Trade Date': 'TradeDate', 'Value Date': 'SettlementDate',
        'Instrument ISIN': 'ISIN', 'Instrument': 'Symbol', 'Type': 'SaxoTransactionType',
        'Event': 'SaxoEventText', 'Booked Amount': 'Amount_Base_Raw', 'Conversion Rate': 'ExchangeRate'
    }

    if 'Kunde-ID' in df.columns: column_mapping = mapping_no
    else: column_mapping = mapping_en
    
    df = df.rename(columns=column_mapping)
    df = df.dropna(subset=['AccountID', 'TradeDate']).copy()
    df['Source'] = 'SAXO'

    df['TradeDate'] = pd.to_datetime(df['TradeDate'], errors='coerce')
    df['SettlementDate'] = pd.to_datetime(df['SettlementDate'], errors='coerce')
    df['Amount_Base_Raw'] = pd.to_numeric(df['Amount_Base_Raw'], errors='coerce').fillna(0)
    df['ExchangeRate'] = pd.to_numeric(df['ExchangeRate'], errors='coerce').fillna(1.0)

    trade_pattern = re.compile(r"(?P<action>Kjøp|Salg|Selg)\s+(?P<quantity>[-]?[-,.]+)\s+@\s+(?P<price>[-,.]+)\s+(?P<currency>-)", re.IGNORECASE)

    processed_rows = []
    for index, row in df.iterrows():
        output_row = {
            'GlobalID': str(uuid.uuid4()), 'Source': 'SAXO', 'AccountID': row['AccountID'],
            'OriginalID': None, 'ParentID': None, 'TradeDate': row['TradeDate'], 
            'SettlementDate': row['SettlementDate'], 'Symbol': row['Symbol'], 'ISIN': row['ISIN'],
            'Description': str(row['SaxoEventText']), 'Quantity': 0.0, 'Price': 0.0,
            'Amount_Base': row['Amount_Base_Raw'], 'Currency_Base': 'NOK',
            'Amount_Local': np.nan, 'Currency_Local': np.nan, 'ExchangeRate': row['ExchangeRate'],
            'SourceFile': os.path.basename(input_file_path),
            'SourceLine': index + 2
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
            saxo_type_text = str(row['SaxoTransactionType']).lower()
            event_text = str(row['SaxoEventText']).lower()
            
            if 'utbytte' in event_text or 'dividend' in event_text: output_row['Type'] = 'DIVIDEND'
            elif 'depotgebyr' in event_text or 'custody fee' in event_text: output_row['Type'] = 'FEE'
            elif 'gebyr' in saxo_type_text or 'fee' in saxo_type_text: output_row['Type'] = 'FEE'
            elif 'rente' in event_text or 'interest' in event_text: output_row['Type'] = 'INTEREST'
            elif 'innskudd' in event_text or 'deposit' in event_text: output_row['Type'] = 'DEPOSIT'
            elif 'uttak' in event_text or 'withdrawal' in event_text: output_row['Type'] = 'WITHDRAWAL'
            else: output_row['Type'] = 'ADJUSTMENT'
            
            if output_row['Type'] in ['FEE', 'WITHDRAWAL']:
                output_row['Amount_Base'] = -abs(row['Amount_Base_Raw'])
            else:
                output_row['Amount_Base'] = abs(row['Amount_Base_Raw'])

            currency_match = re.search(r'\b(USD|EUR|SEK|DKK|CAD|GBP|CHF|JPY|AUD|CNY|HKD|NOK)\b', event_text, re.IGNORECASE)
            
            if not currency_match or currency_match.group(0).upper() == 'NOK':
                output_row['Amount_Local'] = output_row['Amount_Base']
                output_row['Currency_Local'] = 'NOK'
                output_row['ExchangeRate'] = 1.0
            else:
                output_row['Currency_Local'] = currency_match.group(0).upper()
                exchange_rate = row['ExchangeRate'] if row['ExchangeRate'] != 0 else 1.0
                output_row['ExchangeRate'] = exchange_rate
                output_row['Amount_Local'] = output_row['Amount_Base'] / exchange_rate

            processed_rows.append(output_row)

    return pd.DataFrame(processed_rows)

# --- Main Logic ---
def process_new_transactions():
    batch_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_file = setup_logging(batch_id)
    
    logging.info("--- STARTING NEW TRANSACTION IMPORT ---")
    logging.info(f"Batch ID: {batch_id}")
    
    new_raw_path = 'data/new_raw_transactions'
    db_file = 'database/portfolio.db'
    
    # Check for files
    new_files = glob.glob(os.path.join(new_raw_path, '*'))
    new_files = [f for f in new_files if os.path.isfile(f)]
    
    if not new_files:
        logging.warning("No files found in data/new_raw_transactions. Exiting.")
        return

    logging.info(f"Found {len(new_files)} files to process: {[os.path.basename(f) for f in new_files]}")

    # Connect DB
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # 1. Load Existing Hashes
    logging.info("Loading existing transactions to build deduplication map...")
    try:
        existing_df = pd.read_sql_query("SELECT TradeDate, AccountID, Type, Symbol, Amount_Base FROM transactions", conn)
        existing_hashes = set(existing_df.apply(_generate_txn_hash, axis=1))
        logging.info(f"Loaded {len(existing_hashes)} unique transaction hashes from database.")
    except Exception as e:
        logging.error(f"Failed to load existing transactions: {e}")
        return

    all_new_dfs = []
    
    # 2. Process Files
    for file_path in new_files:
        if file_path.endswith('.csv'):
            df = _clean_nordnet_data(file_path)
            all_new_dfs.append(df)
        elif file_path.endswith('.xlsx'):
            df = _clean_saxo_data(file_path)
            all_new_dfs.append(df)
        else:
            logging.warning(f"Skipping unknown file type: {os.path.basename(file_path)}")

    if not all_new_dfs:
        logging.warning("No data extracted from files.")
        return

    # 3. Unify and Deduplicate
    unified_df = pd.concat(all_new_dfs, ignore_index=True)
    
    # Standardizations
    ACCOUNT_TYPE_MAP = {
        19269921: 'Business', 57737694: 'Business',
        24275448: 'Personal', 24275430: 'Personal', 16518125: 'Personal'
    }
    unified_df['AccountType'] = unified_df['AccountID'].map(ACCOUNT_TYPE_MAP)
    
    RENAME_SYMBOLS_MAP = {
        "Floor & Decor Holdings Inc.": "Floor & Decor",
        "iShares Gold Trust": "iShares Gold Trust Shares",
        "ishares Gold Trust": "iShares Gold Trust Shares"
    }
    unified_df['Symbol'] = unified_df['Symbol'].replace(RENAME_SYMBOLS_MAP)
    unified_df['TradeDate'] = pd.to_datetime(unified_df['TradeDate'])
    unified_df['batch_id'] = batch_id
    
    logging.info(f"Total rows read from files: {len(unified_df)}")
    
    rows_to_stage = []
    skipped_count = 0
    
    logging.info("--- Checking for Duplicates ---")
    
    for idx, row in unified_df.iterrows():
        txn_hash = _generate_txn_hash(row)
        desc_short = f"{str(row['TradeDate'])[:10]} | {row['Symbol']} | {row['Amount_Base']}"
        
        if txn_hash in existing_hashes:
            logging.info(f"SKIPPED (Duplicate): {desc_short} (Source: {row.get('SourceFile', '?')}:{row.get('SourceLine', '?')})")
            skipped_count += 1
        else:
            logging.info(f"STAGING (New):       {desc_short}")
            rows_to_stage.append(row)
            # Add to local hash set to prevent duplicates within the same batch
            existing_hashes.add(txn_hash)
            
    logging.info(f"Summary: Staging {len(rows_to_stage)} new transactions. Skipped {skipped_count} duplicates.")

    if not rows_to_stage:
        logging.info("No new transactions to stage. Exiting.")
        return

    # 4. Push to Staging
    final_df = pd.DataFrame(rows_to_stage)
    
    # SQLite Compatibility: Convert Timestamps to Strings
    for col in ['TradeDate', 'SettlementDate']:
        if col in final_df.columns:
            final_df[col] = pd.to_datetime(final_df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # Drop temp columns if they exist
    cols_to_drop = ['SourceFile', 'SourceLine']
    final_df = final_df.drop(columns=[c for c in cols_to_drop if c in final_df.columns])
    
    # Ensure staging table exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions_staging (
            GlobalID TEXT PRIMARY KEY, Source TEXT, AccountID INTEGER, OriginalID REAL,
            ParentID TEXT, TradeDate TEXT, SettlementDate TEXT, Type TEXT, Symbol TEXT,
            ISIN TEXT, Description TEXT, Quantity REAL, Price REAL, Amount_Base REAL,
            Currency_Base TEXT, Amount_Local REAL, Currency_Local TEXT, ExchangeRate TEXT,
            AccountType TEXT, batch_id TEXT
        )
    ''')
    
    try:
        final_df.to_sql('transactions_staging', conn, if_exists='append', index=False)
        logging.info("Successfully wrote to transactions_staging table.")
        
        # Move files
        archive_path = os.path.join(new_raw_path, 'archive')
        os.makedirs(archive_path, exist_ok=True)
        for file_path in new_files:
            dest = os.path.join(archive_path, os.path.basename(file_path))
            os.rename(file_path, dest)
            logging.info(f"Archived file to: {dest}")
            
    except Exception as e:
        logging.error(f"Database error during staging: {e}")
    finally:
        conn.close()
        
    logging.info(f"--- IMPORT COMPLETE. Detailed log saved to: {log_file} ---")
    print(f"\n[SUCCESS] Processed {len(new_files)} files.")
    print(f"Staged: {len(rows_to_stage)} | Skipped: {skipped_count}")
    print(f"Review details in: {log_file}")
    print("Run 'python -m scripts.db.review_staging' to commit.")

if __name__ == '__main__':
    process_new_transactions()