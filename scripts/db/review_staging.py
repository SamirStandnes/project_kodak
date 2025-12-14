import sqlite3
import pandas as pd
from datetime import datetime

def review_staged_transactions():
    """
    Displays transactions from the staging table and provides options to manage them.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    print("--- Review Staged Transactions ---")

    try:
        # Check if staging table is empty
        c.execute("SELECT COUNT(*) FROM transactions_staging")
        count = c.fetchone()[0]

        if count == 0:
            print("The staging area is currently empty. No transactions to review.")
            return

        # Fetch and display staged transactions
        df = pd.read_sql_query("SELECT * FROM transactions_staging", conn)
        print(f"\nFound {count} transaction(s) in the staging area:\n")
        print(df.to_string())

        # Ask for user action
        while True:
            action = input(
                "\nWhat would you like to do?\n"
                "  'commit' - Approve and commit these transactions to the main database.\n"
                "  'clear'  - Delete all transactions from the staging area.\n"
                "  'exit'   - Do nothing and exit the script.\n"
                "Enter your choice: ").lower().strip()

            if action == 'commit':
                commit_staged_transactions(conn)
                break
            elif action == 'clear':
                clear_staging_area(conn)
                break
            elif action == 'exit':
                print("Exiting without making changes.")
                break
            else:
                print("Invalid choice. Please enter 'commit', 'clear', or 'exit'.")

    except sqlite3.OperationalError as e:
        if "no such table: transactions_staging" in str(e):
            print("The staging area has not been created yet. It will be created when you add the first transaction.")
        else:
            raise
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def commit_staged_transactions(conn):
    """Commits transactions from staging to the main transactions table."""
    print("\nCommitting transactions...")
    c = conn.cursor()
    try:
        # Backup before commit (optional but good practice)
        backup_db()
        
        c.execute("INSERT INTO transactions SELECT * FROM transactions_staging")
        print(f"{c.rowcount} transactions committed successfully.")
        
        # Clear staging area after commit
        c.execute("DELETE FROM transactions_staging")
        print("Staging area has been cleared.")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"An error occurred during commit: {e}")
        print("The transaction has been rolled back.")

def clear_staging_area(conn):
    """Deletes all records from the staging table."""
    confirm = input("Are you sure you want to delete all transactions from the staging area? (y/n): ").lower()
    if confirm == 'y':
        c = conn.cursor()
        c.execute("DELETE FROM transactions_staging")
        conn.commit()
        print(f"Staging area cleared. {c.rowcount} transactions were deleted.")
    else:
        print("Clear operation cancelled.")

def backup_db():
    """Creates a timestamped backup of the database."""
    print("Creating database backup...")
    db_file = 'database/portfolio.db'
    backup_file = f"database/portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db.bak"
    try:
        conn = sqlite3.connect(backup_file)
        source_conn = sqlite3.connect(db_file)
        source_conn.backup(conn)
        source_conn.close()
        conn.close()
        print(f"Backup created successfully at {backup_file}")
    except Exception as e:
        print(f"Error creating backup: {e}")

if __name__ == '__main__':
    review_staged_transactions()
