
import pandas as pd
import os

INPUT_FILE = os.path.join('data', 'processed_cash_flows.csv')
OUTPUT_FILE = os.path.join('data', 'unified_transactions_for_review.xlsx')

print(f"Loading processed cash flows from {INPUT_FILE} for Excel export...")
try:
    df = pd.read_csv(INPUT_FILE, parse_dates=['TradeDate', 'SettlementDate'])

    # Select relevant columns for review
    # Original 'Amount' and 'Currency' are useful for cross-referencing
    # 'TransactionType', 'CashFlowCategory' for understanding classification
    # 'TransactionText' for original event description
    columns_for_review = [
        'Source', 'AccountId', 'TradeDate', 'SettlementDate',
        'TransactionType', 'CashFlowCategory', 'Security', 'ISIN',
        'Quantity', 'Price', 'Amount', 'Currency', 'BrokerageFee',
        'CashBalance', 'Amount_NOK', 'TransactionText'
    ]
    
    # Ensure all columns exist before selecting
    existing_columns = [col for col in columns_for_review if col in df.columns]
    df_export = df[existing_columns].copy()

    # Sort for better readability in Excel
    df_export = df_export.sort_values(by=['Source', 'AccountId', 'TradeDate'])

    # Export to Excel
    print(f"Exporting unified transactions to {OUTPUT_FILE} for review...")
    df_export.to_excel(OUTPUT_FILE, index=False, sheet_name='Unified Transactions')
    print(f"Successfully exported data to {OUTPUT_FILE}")

except FileNotFoundError:
    print(f"Error: Processed cash flows file not found at {INPUT_FILE}")
except Exception as e:
    print(f"An error occurred: {e}")
