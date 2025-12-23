import sqlite3
import shutil
from datetime import datetime
import os

def commit_changes():
    db_file = 'database/portfolio.db'
    backup_dir = 'database/backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f'portfolio_before_commit_{timestamp}.db.bak')

    # 1. Create Backup
    try:
        shutil.copy2(db_file, backup_file)
        print(f'Backup created: {backup_file}')
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return

    # 2. Commit Staged Transactions
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        c.execute('INSERT INTO transactions SELECT * FROM transactions_staging')
        rows_added = c.rowcount
        
        c.execute('DELETE FROM transactions_staging')
        
        conn.commit()
        conn.close()
        print(f'Successfully committed {rows_added} transactions to the main database.')
    except Exception as e:
        print(f"Failed to commit transactions: {e}")

if __name__ == "__main__":
    commit_changes()
