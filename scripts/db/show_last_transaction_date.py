import sqlite3
import os
from datetime import datetime

def parse_date_flexible(date_string):
    """
    Parses a date string that could be in one of several formats.
    """
    if not date_string:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date string '{date_string}' could not be parsed with known formats.")


def show_last_transaction_date():
    """
    Connects to the database and prints the date of the most recent transaction
    for each data source.
    """
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'database', 'portfolio.db')
    
    if not os.path.exists(db_file):
        print(f"Error: Database file not found at '{db_file}'")
        return

    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        
        # Query for the overall latest date first
        c.execute("SELECT MAX(TradeDate) FROM transactions")
        overall_last_date_str = c.fetchone()[0]

        if overall_last_date_str:
            overall_last_date = parse_date_flexible(overall_last_date_str)
            print(f"\nOverall last transaction date: {overall_last_date.strftime('%Y-%m-%d')}")
        else:
            print("\nNo transactions found in the database.")
            return # Exit if no transactions at all
        
        print("\nLast transaction date by source:")
        # Query for the latest date per source
        c.execute("SELECT Source, MAX(TradeDate) FROM transactions GROUP BY Source ORDER BY Source")
        
        results = c.fetchall()
        
        if not results:
            print("  - No data found.")
        else:
            for source, last_date_str in results:
                if last_date_str:
                    last_date = parse_date_flexible(last_date_str)
                    print(f"  - {source}: {last_date.strftime('%Y-%m-%d')}")
                else:
                    print(f"  - {source}: No date available")

    except (sqlite3.Error, ValueError) as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    show_last_transaction_date()