
import sqlite3

def swap_tables():
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    # 1. Archive old
    c.execute("ALTER TABLE transactions RENAME TO transactions_old")
    # 2. Promoted V2 to main
    c.execute("ALTER TABLE transactions_v2 RENAME TO transactions")
    # 3. Create a view for backward compatibility (Amount_Base -> Amount_NOK)
    # This allows old scripts to keep working without modification!
    c.execute("CREATE VIEW transactions_compat AS SELECT *, Amount_NOK as Amount_Base FROM transactions")
    conn.commit()
    conn.close()
    print("Table swap successful.")

if __name__ == '__main__':
    swap_tables()
