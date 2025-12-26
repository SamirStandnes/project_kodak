import sqlite3

def fix_dnb_buy_signs():
    db_path = 'database/portfolio.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("Checking for BUY transactions with positive Amount_Base...")
    c.execute("SELECT GlobalID, Amount_Base FROM transactions WHERE Type='BUY' AND Amount_Base > 0")
    rows = c.fetchall()

    if not rows:
        print("No incorrect BUY transactions found.")
        conn.close()
        return

    print(f"Found {len(rows)} transactions to fix.")
    
    for global_id, amount in rows:
        new_amount = -abs(amount)
        print(f"Fixing {global_id}: {amount} -> {new_amount}")
        c.execute("UPDATE transactions SET Amount_Base = ? WHERE GlobalID = ?", (new_amount, global_id))

    conn.commit()
    print("Database updated successfully.")
    conn.close()

if __name__ == "__main__":
    fix_dnb_buy_signs()
