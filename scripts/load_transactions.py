import sqlite3
import pandas as pd

def load_transactions_to_db():
    """
    Loads transaction data from a CSV file into the SQLite database.
    """
    csv_file = 'data/processed/unified_portfolio_data.csv'
    db_file = 'database/portfolio.db'

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Connect to the SQLite database
    conn = sqlite3.connect(db_file)

    # Load the data into the 'transactions' table
    df.to_sql('transactions', conn, if_exists='replace', index=False)

    conn.close()

if __name__ == '__main__':
    load_transactions_to_db()
    print("Transaction data loaded successfully into the database.")
