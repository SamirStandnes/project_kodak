import os
import glob
import pandas as pd
import logging
from datetime import datetime
from scripts.shared.utils import setup_logging, generate_txn_hash
from scripts.shared.db import get_connection, execute_non_query, execute_query
from scripts.pipeline.parsers import parse_nordnet, parse_saxo

RAW_PATH = os.path.join('data', 'new_raw_transactions')
ARCHIVE_PATH = os.path.join(RAW_PATH, 'archive')

def run_ingestion():
    log_file = setup_logging("ingest_new")
    logging.info(f"Starting ingestion process. Log file: {log_file}")
    conn = get_connection()
    
    # 1. Find Files
    files = glob.glob(os.path.join(RAW_PATH, "*"))
    files = [f for f in files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]
    
    if not files:
        logging.info("No new files found in data/new_raw_transactions.")
        return

    logging.info(f"Found {len(files)} files to process.")
    
    # Generate Batch ID
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.info(f"Generated Batch ID: {batch_id}")

    # 2. Parse All
    all_rows = []
    for f in files:
        logging.info(f"Parsing {os.path.basename(f)}...")
        if f.endswith('.csv'):
            all_rows.extend(parse_nordnet(f))
        elif f.endswith('.xlsx'):
            all_rows.extend(parse_saxo(f))
        else:
            logging.warning(f"Skipping unknown file type: {f}")

    if not all_rows:
        logging.warning("No rows extracted.")
        return

    # 3. Load Existing Hashes (Deduplication)
    # We need to join with accounts/instruments to reconstruct the hash inputs if we stored them normalized
    # Or simpler: Just check if 'external_id' exists if we trust the UUID generation (we don't, it's random).
    # We need to hash the *content* of the new rows and compare with existing content.
    
    # Fetch relevant columns from existing transactions to build hash set
    existing_txns = execute_query('''
        SELECT t.date, a.external_id as acc_ext, t.type, i.symbol, t.amount
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        LEFT JOIN instruments i ON t.instrument_id = i.id
    ''')
    
    existing_hashes = set()
    for row in existing_txns:
        h = generate_txn_hash(
            row['date'], row['acc_ext'], row['type'], 
            row['symbol'] if row['symbol'] else '', row['amount']
        )
        existing_hashes.add(h)

    # 4. Filter & Stage
    to_stage = []
    skipped = 0
    
    for item in all_rows:
        h = generate_txn_hash(
            item['date'], item['account_external_id'], item['type'],
            item['symbol'], item['amount']
        )
        
        if h in existing_hashes:
            skipped += 1
            continue
            
        item['hash'] = h
        item['batch_id'] = batch_id
        to_stage.append(item)

    logging.info(f"Staging {len(to_stage)} transactions (Skipped {skipped} duplicates).")
    
    if not to_stage:
        return

    # 5. Write to Staging Table
    # We use a Denormalized Staging Table
    execute_non_query('''
        CREATE TABLE IF NOT EXISTS transactions_staging (
            external_id TEXT,
            account_external_id TEXT,
            isin TEXT,
            symbol TEXT,
            date TEXT,
            type TEXT,
            quantity REAL,
            price REAL,
            amount REAL,
            currency TEXT,
            amount_local REAL,
            exchange_rate REAL,
            fee REAL,
            fee_currency TEXT,
            fee_local REAL,
            description TEXT,
            source_file TEXT,
            hash TEXT,
            batch_id TEXT
        )
    ''')

    # Insert
    # We can use pandas to_sql for convenience with the list of dicts
    df_stage = pd.DataFrame(to_stage)
    
    # Ensure all columns match
    # Convert datetime objects to string
    df_stage['date'] = df_stage['date'].astype(str)
    
    try:
        df_stage.to_sql('transactions_staging', conn, if_exists='append', index=False)
        logging.info("Data pushed to staging.")
        
        # 6. Archive Files
        os.makedirs(ARCHIVE_PATH, exist_ok=True)
        for f in files:
            dest = os.path.join(ARCHIVE_PATH, os.path.basename(f))
            os.replace(f, dest) # robust move
            logging.info(f"Archived {os.path.basename(f)}")
            
    except Exception as e:
        logging.error(f"Error writing to staging: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    run_ingestion()
