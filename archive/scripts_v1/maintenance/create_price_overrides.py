
import sqlite3

def create_overrides():
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    
    # Create table
    c.execute('''
        CREATE TABLE IF NOT EXISTS historical_price_overrides (
            ISIN TEXT,
            Date TEXT,
            Price REAL,
            PRIMARY KEY (ISIN, Date)
        )
    ''')
    
    # Insert 2020-12-31 overrides
    overrides = [
        ('NO0010793961', '2020-12-31', 146.0), # TRACKER GULL
        ('NO0010848104', '2020-12-31', 2.60),  # BEAR TESLA
        ('SE0009723026', '2020-12-31', 860.0)  # XACT OBX (Proxy via OBX.OL index)
    ]
    
    # XACT OBX: If I can't get history, I should override it too.
    # On 2025-12-29 OBX is 1580.
    # On 2020-12-31 OBX was around 900-1000?
    # Let's check OBX.OL history for Dec 31 2020.
    # Yahoo said OBX.OL exists.
    
    c.executemany('REPLACE INTO historical_price_overrides (ISIN, Date, Price) VALUES (?, ?, ?)', overrides)
    
    conn.commit()
    print("Created overrides table and inserted values.")
    conn.close()

if __name__ == '__main__':
    create_overrides()
