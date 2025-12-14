
import pandas as pd
import os

FILE_PATH = os.path.join('data', 'unified_portfolio_data.csv')
OUTPUT_FILE = os.path.join('data', 'processed_cash_flows.csv')

# --- Cash Flow Type Mapping ---
# Map cleaned TransactionType to a generic cash flow category
CASH_FLOW_CATEGORY_MAP = {
    'Buy': 'Capital_Out',
    'Sell': 'Capital_In',
    'Deposit': 'Capital_In',
    'Withdrawal': 'Capital_Out',
    'Trade': 'Capital_Out', # Assuming trades are buys here, will need more logic for short sells
    'CFD Trade': 'Capital_Out', # Assuming CFD trades are initial capital outlays
    
    'Debit Interest': 'Expense',
    'Dividend': 'Income',
    'Currency Sell': 'Capital_In', # Proceeds from selling currency
    'Currency Buy': 'Capital_Out', # Cost of buying currency
    'Platform Fee': 'Expense',
    'Coupon Tax': 'Expense',
    'Fee': 'Expense',
    'German Tax': 'Expense',
    'Overdraft Interest': 'Expense',
    'Rebate Allocation': 'Income',
    'Fund Fee Refund': 'Income',
    'Redemption Withdrawal': 'Capital_Out', # Withdrawal of capital
    'Fee Correction': 'Income', # Assuming a positive correction
    'Spin-off/Merger': 'Capital_In', # Often involves receiving new securities/cash
    'Security Exchange In': 'Capital_In', # Receiving security
    'Security Exchange Out': 'Capital_Out', # Giving up security
    'Deletion Withdrawal': 'Capital_Out',
    'Cash Deposit': 'Capital_In',
    'Compensation': 'Income',
    'Issue Deposit': 'Capital_In',
    'CFD Fee': 'Expense'
}

# --- Placeholder Exchange Rates (for illustration, need historical in real scenario) ---
# Assuming NOK is base currency
EXCHANGE_RATES = {
    'NOK': 1.0,
    'USD': 10.0, # Placeholder: 1 USD = 10 NOK
    'EUR': 10.5  # Placeholder: 1 EUR = 10.5 NOK
}

def process_unified_data(df):
    # Apply cash flow category mapping
    df['CashFlowCategory'] = df['TransactionType'].map(CASH_FLOW_CATEGORY_MAP)
    
    # Ensure 'Amount' column is numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    
    # Standardize signs based on CashFlowCategory and Amount
    def standardize_amount_sign(row):
        amount = row['Amount']
        cf_category = row['CashFlowCategory']

        if pd.isna(amount) or pd.isna(cf_category):
            return amount
        
        if cf_category in ['Capital_Out', 'Expense', 'Buy', 'Withdrawal', 'Trade', 'CFD Trade', 'Currency Buy',
                          'Debit Interest', 'Platform Fee', 'Coupon Tax', 'Fee', 'German Tax', 'Overdraft Interest',
                          'Redemption Withdrawal', 'Security Exchange Out', 'Deletion Withdrawal', 'CFD Fee']:
            return -abs(amount) # Ensure it's negative
        elif cf_category in ['Capital_In', 'Income', 'Sell', 'Deposit', 'Dividend', 'Currency Sell', 'Rebate Allocation',
                            'Fund Fee Refund', 'Fee Correction', 'Spin-off/Merger', 'Security Exchange In',
                            'Cash Deposit', 'Compensation', 'Issue Deposit']:
            return abs(amount) # Ensure it's positive
        return amount # Should not happen if all categories are covered

    df['AdjustedAmount'] = df.apply(standardize_amount_sign, axis=1)

    # Convert to Base Currency (NOK)
    def convert_to_base_currency(row):
        if pd.isna(row['AdjustedAmount']):
            return row['AdjustedAmount']
        if row['Currency'] == 'NOK':
            return row['AdjustedAmount']
        elif row['Currency'] in EXCHANGE_RATES:
            return row['AdjustedAmount'] * EXCHANGE_RATES[row['Currency']]
        print(f"Warning: Unknown currency '{row['Currency']}' for Amount '{row['AdjustedAmount']}'. Skipping conversion.")
        return row['AdjustedAmount'] # Return original adjusted amount if currency unknown

    df['Amount_NOK'] = df.apply(convert_to_base_currency, axis=1)
    
    return df

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Loading unified data from {FILE_PATH}...")
    try:
        unified_df = pd.read_csv(FILE_PATH, parse_dates=['TradeDate', 'SettlementDate'])

        print("Categorizing cash flows and converting amounts to NOK...")
        processed_df = process_unified_data(unified_df.copy())

        # Save the processed DataFrame
        processed_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print(f"\nProcessed cash flows saved to {OUTPUT_FILE}")

        # Display info of the processed DataFrame
        print("\nProcessed Cash Flows DataFrame Info:")
        processed_df.info()
        print("\nProcessed Cash Flows DataFrame Head:")
        print(processed_df.head())
        print("\nCash Flow Category Counts:")
        print(processed_df['CashFlowCategory'].value_counts())
        print("\nAmount_NOK Statistics:")
        print(processed_df['Amount_NOK'].describe())


    except FileNotFoundError:
        print(f"Error: Unified data file not found at {FILE_PATH}")
    except Exception as e:
        print(f"An error occurred: {e}")
