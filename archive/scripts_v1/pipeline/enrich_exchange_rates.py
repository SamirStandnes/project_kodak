import sqlite3
import pandas as pd
import sys
import os

# Ensure shared directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.shared.market_data import get_exchange_rate
from scripts.shared.db import get_db_connection

def enrich_missing_exchange_rates():
    """
    Scans the database for transactions with missing exchange rates
    and enriches them by fetching historical rates.
    """
    conn = None
    updated_count = 0
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Find transactions that need enrichment
        # Look for non-NOK transactions where ExchangeRate is NULL, 0, or an empty string
        c.execute('''
            SELECT GlobalID, TradeDate, Currency_Local, Currency_Base
            FROM transactions
            WHERE (ExchangeRate IS NULL OR ExchangeRate = 0 OR ExchangeRate = '')
              AND Currency_Local IS NOT NULL
              AND Currency_Local != 'NOK'
        ''')
        
        transactions_to_enrich = c.fetchall()
        
        if not transactions_to_enrich:
            print("No transactions found needing exchange rate enrichment.")
            return

        print(f"Found {len(transactions_to_enrich)} transactions to enrich with exchange rates...")

        for global_id, trade_date, currency_local, currency_base in transactions_to_enrich:
            if not trade_date or not currency_local:
                continue

            print(f"Fetching rate for {global_id} ({currency_local} to NOK on {trade_date})...", end='')
            
            # Use the new utility function to get the historical rate
            historical_rate = get_exchange_rate(currency_local, target_currency='NOK', date=trade_date)
            
            if historical_rate:
                # Update the database with the fetched rate
                c.execute('''
                    UPDATE transactions
                    SET ExchangeRate = ?
                    WHERE GlobalID = ?
                ''', (historical_rate, global_id))
                print(f" Success. Rate: {historical_rate:.4f}")
                updated_count += 1
            else:
                print(" Failed.")

        conn.commit()
        print(f"\nEnrichment complete. Updated {updated_count} transactions.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    enrich_missing_exchange_rates()