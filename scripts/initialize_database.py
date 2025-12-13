import sqlite3

def initialize_database():
    """
    Initializes the SQLite database and creates the necessary tables.
    """
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()

    # Create transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            GlobalID TEXT PRIMARY KEY,
            Source TEXT,
            AccountID TEXT,
            OriginalID TEXT,
            ParentID TEXT,
            TradeDate TEXT,
            SettlementDate TEXT,
            Type TEXT,
            Symbol TEXT,
            ISIN TEXT,
            Description TEXT,
            Quantity REAL,
            Price REAL,
            Amount_Base REAL,
            Currency_Base TEXT,
            Amount_Local REAL,
            Currency_Local TEXT,
            ExchangeRate REAL,
            AccountType TEXT
        )
    ''')

    # Create ISIN to Symbol mapping table
    c.execute('''
        CREATE TABLE IF NOT EXISTS isin_symbol_map (
            ISIN TEXT PRIMARY KEY,
            Symbol TEXT NOT NULL,
            Currency TEXT
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    initialize_database()
    print("Database initialized successfully.")
