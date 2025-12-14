import sqlite3
import pandas as pd
import os

DB_FILE = 'database/portfolio.db'
MAPPING_FILE = 'isin_map.csv'

def load_mappings_from_csv():
    """
    Loads the ISIN to Symbol/Currency mappings from the CSV file into a dictionary.
    """
    if not os.path.exists(MAPPING_FILE):
        return {}
    
    try:
        df = pd.read_csv(MAPPING_FILE)
        # Create a dictionary where key is ISIN and value is another dict {'Symbol': xxx, 'Currency': yyy}
        mapping_dict = df.set_index('ISIN').to_dict('index')
        return mapping_dict
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return {}

def save_mapping_to_csv(isin, symbol, currency):
    """
    Appends a new mapping to the CSV file.
    """
    new_mapping = pd.DataFrame([{'ISIN': isin, 'Symbol': symbol, 'Currency': currency}])
    
    # Check if file exists and is not empty to decide on writing header
    file_exists = os.path.exists(MAPPING_FILE) and os.path.getsize(MAPPING_FILE) > 0
    
    new_mapping.to_csv(MAPPING_FILE, mode='a', header=not file_exists, index=False)

def get_all_holdings():
    """
    Gets the ISIN and description for all currently held securities that don't have a mapping yet.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Select ISINs that are in transactions but not in isin_symbol_map
    c.execute('''
        SELECT DISTINCT T.ISIN, T.Description
        FROM transactions T
        LEFT JOIN isin_symbol_map M ON T.ISIN = M.ISIN
        WHERE T.ISIN IS NOT NULL AND M.ISIN IS NULL
        AND T.ISIN IN (
            SELECT ISIN FROM transactions WHERE ISIN IS NOT NULL GROUP BY ISIN HAVING SUM(Quantity) > 0
        )
    ''')
    unmapped_holdings = c.fetchall()
    conn.close()
    return unmapped_holdings

def sync_maps_to_db():
    """
    Synchronizes all mappings from the CSV file to the database.
    This ensures the database is always up to date with the CSV.
    """
    mappings_from_csv = load_mappings_from_csv()
    if not mappings_from_csv:
        print("No mappings found in CSV file to sync to DB.")
        return

    # Transform the dictionary into a list of tuples for executemany
    db_mappings = [
        (isin, data['Symbol'], data['Currency'])
        for isin, data in mappings_from_csv.items()
    ]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Use REPLACE to insert new mappings or update existing ones
    c.executemany('REPLACE INTO isin_symbol_map (ISIN, Symbol, Currency) VALUES (?, ?, ?)', db_mappings)
    conn.commit()
    conn.close()
    print(f"Synchronized {len(db_mappings)} mappings from {MAPPING_FILE} to the database.")

def map_isins_and_currencies():
    """
    Prompts the user to map any unmapped ISINs to ticker symbols and currencies,
    saving the result to a CSV file and updating the database.
    """
    # First, ensure the DB is up-to-date with the CSV file
    sync_maps_to_db()

    # Then, find any holdings that are still unmapped
    unmapped_holdings = get_all_holdings()

    if not unmapped_holdings:
        print("All current holdings are already mapped.")
        return

    print("\nPlease provide the ticker symbol and currency for the following new securities:")
    
    for isin, description in unmapped_holdings:
        # Prompt for symbol
        symbol_prompt = f"  - {description} ({isin})\n    Symbol: "
        new_symbol = input(symbol_prompt).strip()

        # Prompt for currency
        currency_prompt = f"    Currency: "
        new_currency = input(currency_prompt).strip().upper()
        
        if new_symbol and new_currency:
            save_mapping_to_csv(isin, new_symbol, new_currency)
            print(f"Saved mapping for {new_symbol}.")
        else:
            print(f"Skipping mapping for {isin} due to empty input.")

    # Finally, re-sync to get the newly added mappings into the DB for the current session
    print("\nRe-syncing new mappings to the database...")
    sync_maps_to_db()

if __name__ == '__main__':
    map_isins_and_currencies()