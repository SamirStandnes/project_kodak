import pandas as pd

def analyze_account_portfolio(account_id, file_path='portfolio_schema.xlsx'):
    df = pd.read_excel(file_path)

    # Filter for the specific account and exclude FEE transactions
    account_df = df[(df['AccountID'] == account_id) & (df['Type'] != 'FEE')].copy()

    if account_df.empty:
        print(f"No transactions found for AccountID: {account_id} (excluding fees).")
        return

    # Group by ISIN to consolidate holdings of the same security, regardless of symbol changes
    # For each ISIN, sum Quantity and Amount, and take the last symbol name and settlement date
    portfolio_summary = account_df.groupby('ISIN').agg(
        Last_Symbol=('Symbol', 'last'),
        Net_Quantity=('Quantity', 'sum'),
        Net_Cash_Flow_Base_Currency=('Amount_Base', 'sum'),
        Last_Date=('SettlementDate', 'max') # To help in selecting the most recent symbol
    ).reset_index()

    # Rename 'Last_Symbol' to 'Symbol' for the final output
    portfolio_summary.rename(columns={'Last_Symbol': 'Symbol'}, inplace=True)

    # Filter out symbols with zero net quantity or negligible quantities
    threshold = 1e-6
    portfolio_summary = portfolio_summary[portfolio_summary['Net_Quantity'].abs() > threshold].copy()

    if portfolio_summary.empty:
        print(f"No open positions (Net Quantity != 0) found for AccountID: {account_id} (excluding fees).")
        return

    # Format output for better readability
    portfolio_summary['Net_Cash_Flow_Base_Currency'] = portfolio_summary['Net_Cash_Flow_Base_Currency'].round(2)
    
    # Select and reorder columns for the final report
    final_columns = ['Symbol', 'ISIN', 'Net_Quantity', 'Net_Cash_Flow_Base_Currency']
    portfolio_summary = portfolio_summary[final_columns]

    print(f"Corrected Portfolio Summary for AccountID: {account_id} (Grouped by ISIN)")
    print("Note: 'Net Cash Flow (Base Currency)' represents the aggregate capital moved in/out for that symbol.")
    print("      A negative value generally indicates total capital invested, a positive value indicates capital returned.")
    print("      This is NOT a cost basis calculation for currently held shares, which requires specific accounting methods.")
    print(portfolio_summary.to_markdown(index=False))

if __name__ == "__main__":
    target_account_id = 24275430
    analyze_account_portfolio(target_account_id)
