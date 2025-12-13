import pandas as pd
import os

FILE_PATH = os.path.join('data', 'unified_portfolio_data.csv')

print(f"Loading and analyzing unified data from {FILE_PATH}...")
try:
    df = pd.read_csv(FILE_PATH, parse_dates=['TradeDate', 'SettlementDate'])

    print("\n--- Unified Data Overview ---")
    print(f"Total records: {len(df)}")
    print(f"Data time range: {df['TradeDate'].min().strftime('%Y-%m-%d')} to {df['TradeDate'].max().strftime('%Y-%m-%d')}")

    print("\n--- Transaction Type Counts by Source ---")
    print(df.groupby('Source')['TransactionType'].value_counts())

    print("\n--- Amount Statistics (Overall) ---")
    print(df['Amount'].describe())

    print("\n--- Currencies in Data ---")
    print(df['Currency'].value_counts())

    print("\n--- Top 10 Securities by Amount ---")
    # Filter for Buy/Sell/Trade transactions and sum absolute amounts
    trade_like_transactions = ['Buy', 'Sell', 'Trade', 'CFD Trade']
    security_df = df[df['TransactionType'].isin(trade_like_transactions)].copy()
    if not security_df.empty:
        security_df['AbsAmount'] = security_df['Amount'].abs()
        top_securities = security_df.groupby('Security')['AbsAmount'].sum().nlargest(10)
        print(top_securities)
    else:
        print("No 'Buy', 'Sell', 'Trade', or 'CFD Trade' transactions with securities found.")

    print("\n--- Transaction Types NOT considered for direct IRR/TWR calculation (initial look) ---")
    # These are types that might need special handling or exclusion from direct capital flows
    irrelevant_for_simple_irr = ['Fee', 'Debit Interest', 'Platform Fee', 'Coupon Tax', 'German Tax',
                                 'Overdraft Interest', 'CFD Fee', 'Currency Sell', 'Currency Buy',
                                 'Fee Correction', 'Spin-off/Merger', 'Security Exchange In',
                                 'Security Exchange Out', 'Deletion Withdrawal', 'Compensation',
                                 'Issue Deposit', 'Redemption Withdrawal', 'Rebate Allocation', 'Cash Deposit']
    non_capital_flow_types = df[~df['TransactionType'].isin(['Buy', 'Sell', 'Deposit', 'Withdrawal', 'Trade', 'CFD Trade'])]
    if not non_capital_flow_types.empty:
        print(non_capital_flow_types['TransactionType'].value_counts())
    else:
        print("All transactions are 'Buy', 'Sell', 'Deposit', 'Withdrawal', 'Trade', or 'CFD Trade'.")

except FileNotFoundError:
    print(f"Error: Unified data file not found at {FILE_PATH}")
except Exception as e:
    print(f"An error occurred: {e}")
