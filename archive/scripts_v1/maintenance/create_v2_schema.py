import sqlite3
import os

DB_PATH = 'database/portfolio_v2.db'

def create_schema():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # --- 1. Master Data ---

    # Accounts: The containers for assets
    c.execute('''
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            broker TEXT,
            currency TEXT NOT NULL DEFAULT 'NOK', -- Reporting currency
            type TEXT,
            external_id TEXT UNIQUE -- The ID from the import file (e.g. 19269921)
        )
    ''')

    # Instruments: The tradable assets
    c.execute('''
        CREATE TABLE instruments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isin TEXT UNIQUE,
            symbol TEXT,
            name TEXT,
            type TEXT,
            currency TEXT,
            exchange_mic TEXT
        )
    ''')

    # --- 2. The Ledger ---

    # Transactions: The events
    c.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE, -- GlobalID from old DB
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            instrument_id INTEGER REFERENCES instruments(id),
            
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            
            quantity REAL,
            price REAL,
            
            amount REAL,           -- In transaction currency (Currency_Raw)
            currency TEXT NOT NULL,
            
            exchange_rate REAL,    -- To convert to Account Currency
            amount_local REAL,     -- In Account Currency (Amount_NOK)
            
            fee REAL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')

    # --- 3. Market Data ---

    c.execute('''
        CREATE TABLE market_prices (
            instrument_id INTEGER NOT NULL REFERENCES instruments(id),
            date TEXT NOT NULL,
            close REAL,
            currency TEXT,
            source TEXT,
            PRIMARY KEY (instrument_id, date)
        )
    ''')

    c.execute('''
        CREATE TABLE exchange_rates (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            rate REAL,
            PRIMARY KEY (from_currency, to_currency, date)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Created schema in {DB_PATH}")

if __name__ == '__main__':
    create_schema()
