import sqlite3
import uuid
from datetime import datetime
from scripts.pipeline.utils import get_exchange_rate

def create_staging_table(conn):
    """Creates the transactions_staging table if it doesn't exist."""
    c = conn.cursor()
    # Schema reflects the main transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions_staging (
            GlobalID TEXT PRIMARY KEY,
            Source TEXT,
            AccountID INTEGER,
            OriginalID REAL,
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
            ExchangeRate TEXT,
            AccountType TEXT,
            batch_id TEXT
        )
    ''')
    conn.commit()

def get_user_input(prompt, required=True, input_type=str):
    """A helper function to get validated user input."""
    while True:
        val = input(f"{prompt}: ").strip()
        if not val and required:
            print("This field is required.")
            continue
        if not val and not required:
            return None
        try:
            return input_type(val)
        except ValueError:
            print(f"Invalid input. Please enter a value of type {input_type.__name__}")

def add_manual_transaction():
    """Adds one or more transactions manually to the staging table."""
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    
    print("--- Add Manual Transaction ---")
    print("Enter transaction details. Press Ctrl+C to exit.")
    
    # Ensure staging table exists
    create_staging_table(conn)

    while True:
        try:
            print("\n--- New Transaction ---")
            
            # --- Get Transaction Details from User ---
            # Most of these are nullable in the DB, but we'll require key ones.
            trade_date = get_user_input("Trade Date (YYYY-MM-DD)", required=True)
            symbol = get_user_input("Symbol/Ticker", required=True)
            trans_type = get_user_input("Type (e.g., BUY, SELL, DIVIDEND)", required=True).upper()
            quantity = get_user_input("Quantity", required=True, input_type=float)
            price = get_user_input("Price (in local currency)", required=True, input_type=float)
            currency_local = get_user_input("Local Currency (e.g., USD, NOK)", required=True).upper()
            account_id = get_user_input("Account ID", required=True, input_type=int)
            source = get_user_input("Broker/Source (e.g., DNB)", required=True)

            # Optional fields
            isin = get_user_input("ISIN", required=False)
            settlement_date = get_user_input("Settlement Date (YYYY-MM-DD)", required=False)
            
            # --- Auto-generate Fields ---
            global_id = str(uuid.uuid4())
            batch_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            amount_local = quantity * price
            
            # --- Handle Exchange Rate and Base Amount ---
            exchange_rate = 1.0
            amount_base = amount_local
            
            if currency_local != 'NOK':
                manual_rate_choice = input(f"Do you know the exchange rate for {currency_local}/NOK on {trade_date}? (y/n): ").lower()
                if manual_rate_choice == 'y':
                    exchange_rate = get_user_input("Enter Exchange Rate", required=True, input_type=float)
                    amount_base = amount_local * exchange_rate
                    print(f"Using manual rate: {exchange_rate:.4f}. Calculated base amount: {amount_base:,.2f} NOK")
                else:
                    print(f"Looking up historical exchange rate for {currency_local}/NOK on {trade_date}...")
                    rate = get_exchange_rate(currency_local, 'NOK', trade_date)
                    if rate:
                        exchange_rate = rate
                        amount_base = amount_local * exchange_rate
                        print(f"Found rate: {exchange_rate:.4f}. Calculated base amount: {amount_base:,.2f} NOK")
                    else:
                        print("Warning: Could not fetch exchange rate. Amount_Base will be incorrect.")
                        amount_base = None # Set to None if rate fails
            
            # --- Prepare Data for Insertion ---
            transaction_data = {
                'GlobalID': global_id,
                'Source': source,
                'AccountID': account_id,
                'OriginalID': None,
                'ParentID': None,
                'TradeDate': trade_date,
                'SettlementDate': settlement_date,
                'Type': trans_type,
                'Symbol': symbol,
                'ISIN': isin,
                'Description': f"Manual entry for {quantity} {symbol} @ {price}",
                'Quantity': quantity,
                'Price': price,
                'Amount_Base': amount_base,
                'Currency_Base': 'NOK',
                'Amount_Local': amount_local,
                'Currency_Local': currency_local,
                'ExchangeRate': exchange_rate,
                'AccountType': 'Personal', # Default value
                'batch_id': batch_id
            }

            # --- Insert into Staging Table ---
            c = conn.cursor()
            columns = ', '.join(transaction_data.keys())
            placeholders = ', '.join('?' * len(transaction_data))
            sql = f'INSERT INTO transactions_staging ({columns}) VALUES ({placeholders})'
            c.execute(sql, list(transaction_data.values()))
            conn.commit()

            print(f"\nSuccessfully added transaction to staging area with batch_id: {batch_id}")

            another = input("Add another transaction? (y/n): ").lower()
            if another != 'y':
                break

        except KeyboardInterrupt:
            print("\nExiting manual entry.")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            conn.rollback()

    conn.close()
    print("\n--- Manual entry session complete. ---")
    print("Run the 'review_staging.py' script to check your entries.")

if __name__ == '__main__':
    add_manual_transaction()
