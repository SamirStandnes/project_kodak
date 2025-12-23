import sqlite3
import shutil
import os
from datetime import datetime

def revert_last_batch():
    db_file = 'database/portfolio.db'
    target_batch_id = 'file_import_20251223_163008'
    
    # 1. Backup
    backup_dir = 'database/backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"portfolio_before_revert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db.bak")
    shutil.copy2(db_file, backup_path)
    print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # 2. Verify what we are deleting
    c.execute("SELECT GlobalID, TradeDate, Symbol, Amount_Base FROM transactions WHERE batch_id = ?", (target_batch_id,))
    rows = c.fetchall()
    
    if not rows:
        print(f"No transactions found for batch {target_batch_id}. Aborting.")
        conn.close()
        return

    print(f"\nDeleting {len(rows)} transactions from batch '{target_batch_id}':")
    for row in rows:
        print(f" - {row[1]} | {row[2]} | {row[3]}")

    # 3. Delete
    c.execute("DELETE FROM transactions WHERE batch_id = ?", (target_batch_id,))
    deleted_count = c.rowcount
    conn.commit()
    print(f"\nSuccessfully deleted {deleted_count} transactions.")

    # 4. Verify Latest Nordnet Date
    print("\n--- Verification: Latest Nordnet Transactions ---")
    c.execute("SELECT TradeDate, Symbol, Amount_Base FROM transactions WHERE Source = 'Nordnet' ORDER BY TradeDate DESC LIMIT 3")
    latest_rows = c.fetchall()
    for row in latest_rows:
        print(f" {row[0]} | {row[1]} | {row[2]}")

    conn.close()

if __name__ == "__main__":
    revert_last_batch()
