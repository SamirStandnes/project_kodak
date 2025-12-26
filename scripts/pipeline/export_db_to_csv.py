import sqlite3
import pandas as pd
import os
import logging

def export_db_to_csv():
    """
    Exports the current state of the 'transactions' table in the database
    to the legacy CSV format expected by reporting tools.
    """
    db_file = 'database/portfolio.db'
    output_csv = 'data/exports/unified_portfolio_data.csv'
    output_xlsx = 'data/exports/unified_portfolio_data.xlsx'
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    conn = sqlite3.connect(db_file)
    
    try:
        print(f"Reading from database: {db_file}")
        # Read from DB
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
        
        # Sort by TradeDate to keep it clean
        if 'TradeDate' in df.columns:
            df['TradeDate'] = pd.to_datetime(df['TradeDate'], format='mixed')
            df = df.sort_values(by='TradeDate', ascending=True)
        
        print(f"Exporting {len(df)} transactions...")
        
        # Export to CSV
        df.to_csv(output_csv, index=False)
        print(f"Saved CSV to: {output_csv}")
        
        # Export to Excel (optional, but good for quick viewing)
        df.to_excel(output_xlsx, index=False)
        print(f"Saved Excel to: {output_xlsx}")
        
    except Exception as e:
        print(f"Error exporting database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_db_to_csv()