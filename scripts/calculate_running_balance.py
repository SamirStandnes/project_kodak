
import pandas as pd
import os

INPUT_FILE = os.path.join('data', 'unified_portfolio_data_final.csv')
OUTPUT_CSV_FILE = os.path.join('data', 'final_data_with_running_balance.csv')
OUTPUT_EXCEL_FILE = os.path.join('data', 'final_data_with_running_balance.xlsx')

# --- Placeholder Exchange Rates (from process_cash_flows.py) ---
EXCHANGE_RATES = {
    'NOK': 1.0,
    'USD': 10.0,
    'EUR': 10.5
}

print(f"Loading data from {INPUT_FILE}...")
try:
    df = pd.read_csv(INPUT_FILE, parse_dates=['TradeDate', 'SettlementDate'])

    # --- Re-apply currency conversion to create Amount_NOK ---
    def convert_to_base_currency(row):
        if pd.isna(row['Amount']):
            return row['Amount']
        # Default to NOK if Currency is NaN or unknown
        currency = row['Currency'] if isinstance(row['Currency'], str) and pd.notna(row['Currency']) else 'NOK'
        exchange_rate = EXCHANGE_RATES.get(currency, 1.0)
        return row['Amount'] * exchange_rate
    
    df['Amount_NOK'] = df.apply(convert_to_base_currency, axis=1)
    print("Created 'Amount_NOK' column with currency conversion.")

    # --- Calculate Running Cash Balance ---
    # Sort by AccountId and TradeDate
    df = df.sort_values(by=['AccountId', 'TradeDate'])

    # Calculate RunningCashBalance for each AccountId
    df['RunningCashBalance'] = df.groupby('AccountId')['Amount_NOK'].cumsum()
    print("Calculated running cash balance for each account.")

    # Save to new CSV and Excel files
    print(f"Saving data with running cash balance to {OUTPUT_CSV_FILE}...")
    df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"Saving data with running cash balance to {OUTPUT_EXCEL_FILE}...")
    df.to_excel(OUTPUT_EXCEL_FILE, index=False, sheet_name='Transactions with Balance')
    print("Export completed.")

    print("\nHead of the new DataFrame with RunningCashBalance:")
    print(df.head())
    print("\nTail of the new DataFrame with RunningCashBalance:")
    print(df.tail())

except FileNotFoundError:
    print(f"Error: Input file not found at {INPUT_FILE}")
except Exception as e:
    print(f"An error occurred: {e}")
