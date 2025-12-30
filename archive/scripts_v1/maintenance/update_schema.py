
import sqlite3

db_path = 'database/portfolio.db'

def add_column():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check existing columns
    cursor.execute("PRAGMA table_info(isin_symbol_map)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # 2. Add InstrumentType if it doesn't exist
    if 'InstrumentType' not in columns:
        print("Adding 'InstrumentType' column...")
        cursor.execute("ALTER TABLE isin_symbol_map ADD COLUMN InstrumentType TEXT")
        conn.commit()
    else:
        print("'InstrumentType' column already exists.")

    conn.close()

if __name__ == "__main__":
    add_column()
