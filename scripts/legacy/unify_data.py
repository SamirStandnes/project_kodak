import pandas as pd
import glob
import os

def unify_data():
    """
    Finds all cleaned data files, unifies them into a single DataFrame,
    and saves the result.
    """
    processed_path = 'data/processed/'
    
    # Find all cleaned files
    nordnet_file = os.path.join(processed_path, 'nordnet_cleaned.xlsx')
    saxo_files = glob.glob(os.path.join(processed_path, 'saxo_cleaned_*.xlsx'))
    
    all_files = [nordnet_file] + saxo_files
    
    df_list = []
    
    print("--- Starting unification process ---")
    for file in all_files:
        if os.path.exists(file):
            print(f"Reading {os.path.basename(file)}...")
            df = pd.read_excel(file)
            df_list.append(df)
        else:
            print(f"Warning: File not found - {file}")
            
    if not df_list:
        print("No data files found to unify. Exiting.")
        return

    # Concatenate all dataframes
    unified_df = pd.concat(df_list, ignore_index=True)

    # --- Add AccountType Column ---
    ACCOUNT_TYPE_MAP = {
        19269921: 'Business',
        57737694: 'Business',
        24275448: 'Personal',
        24275430: 'Personal',
        16518125: 'Personal'
    }
    # AccountID column is int64, so keys in map should be integers
    unified_df['AccountType'] = unified_df['AccountID'].map(ACCOUNT_TYPE_MAP)

    # --- Standardize Symbol Names ---
    RENAME_SYMBOLS_MAP = {
        "Floor & Decor Holdings Inc.": "Floor & Decor",
        "iShares Gold Trust": "iShares Gold Trust Shares",
        "ishares Gold Trust": "iShares Gold Trust Shares"
    }
    unified_df['Symbol'] = unified_df['Symbol'].replace(RENAME_SYMBOLS_MAP)
    
    # Sort by date
    unified_df['TradeDate'] = pd.to_datetime(unified_df['TradeDate'])
    unified_df = unified_df.sort_values(by='TradeDate').reset_index(drop=True)
    
    # Save the unified file
    output_file_csv = os.path.join(processed_path, 'unified_portfolio_data.csv')
    output_file_xlsx = os.path.join(processed_path, 'unified_portfolio_data.xlsx')
    
    unified_df.to_csv(output_file_csv, index=False)
    unified_df.to_excel(output_file_xlsx, index=False)
    
    print(f"\nUnification complete. Unified data saved to:")
    print(f"- {output_file_csv}")
    print(f"- {output_file_xlsx}")
    
    print("\n--- Unified DataFrame Info ---")
    unified_df.info()

if __name__ == "__main__":
    unify_data()