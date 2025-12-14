import pandas as pd
import os
import re

# --- Configuration ---
# List of files and their corresponding sheet names
SAXO_FILES_CONFIG = [
    {'input_file': os.path.join('data', 'AccountStatement_16518125_2021-12-01_2025-12-09.xlsx'),
     'sheet_name': 'Account Statement 676568INET',
     'output_file': os.path.join('data', 'cleaned_saxo_676568INET.csv')}, # Renamed for clarity
    {'input_file': os.path.join('data', 'AccountStatement_19269921_2023-01-01_2025-12-09.xlsx'),
     'sheet_name': 'Kontoutdrag 877497INET', # Correct sheet name for second file
     'output_file': os.path.join('data', 'cleaned_saxo_877497INET.csv')}  # Renamed for clarity
]

# --- Column Name Translations for both English and Norwegian ---
ENGLISH_TO_STANDARDIZED = {
    'Account ID': 'AccountId',
    'Posting Date': 'TradeDate',
    'Value Date': 'SettlementDate',
    'Net Change': 'Amount',
    'Event': 'TransactionText',
    'Cash Balance': 'CashBalance' # Added for consistency
}

NORWEGIAN_TO_STANDARDIZED = {
    'Konto-ID': 'AccountId',
    'Posteringsdato': 'TradeDate',
    'Valuteringsdato': 'SettlementDate',
    'Netto endring': 'Amount',
    'Hendelse': 'TransactionText',
    'Kontantbeholdning': 'CashBalance' # Added for consistency
}

# --- Norwegian Month Mapping ---
NORWEGIAN_MONTH_MAP = {
    'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'mai': 'May', 'jun': 'Jun',
    'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'des': 'Dec'
}

def replace_norwegian_months(date_series):
    # Ensure it's string type first, then replace month abbreviations
    # Only process if not already datetime to avoid errors on already parsed dates
    if pd.api.types.is_object_dtype(date_series):
        date_series = date_series.astype(str)
        for nor, eng in NORWEGIAN_MONTH_MAP.items():
            date_series = date_series.str.replace(nor, eng, flags=re.IGNORECASE)
    return date_series


def clean_saxo_data(input_file_path, sheet_name, output_file_path):
    """
    Cleans and structures the Saxo Bank Excel statement from a specific sheet.
    """
    print(f"Processing '{os.path.basename(input_file_path)}' from sheet '{sheet_name}'...")
    try:
        df = pd.read_excel(input_file_path, sheet_name=sheet_name)
    except ValueError as e:
        print(f"Error loading sheet '{sheet_name}' from '{input_file_path}': {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    
    # Determine which set of column names are present and apply appropriate renaming
    current_columns = df.columns.tolist()
    if 'Posting Date' in current_columns: # Assume English headers
        df = df.rename(columns=ENGLISH_TO_STANDARDIZED)
    elif 'Posteringsdato' in current_columns: # Assume Norwegian headers
        df = df.rename(columns=NORWEGIAN_TO_STANDARDIZED)
    else:
        print(f"Warning: Unknown column headers in {input_file_path}. Skipping rename for now.")

    # Drop empty columns (assuming 'Kommentar'/'Comment' is consistently empty or irrelevant)
    # Check if 'Kommentar' or 'Comment' column exists before dropping to avoid KeyError
    if 'Kommentar' in df.columns:
        df = df.drop(columns=['Kommentar'])
    elif 'Comment' in df.columns:
        df = df.drop(columns=['Comment'])
    
    # Replace Norwegian month abbreviations before parsing
    df['TradeDate'] = replace_norwegian_months(df['TradeDate'])
    df['SettlementDate'] = replace_norwegian_months(df['SettlementDate'])

    # Convert date columns with explicit DD-Mon-YYYY format
    df['TradeDate'] = pd.to_datetime(df['TradeDate'], errors='coerce', format='%d-%b-%Y')
    df['SettlementDate'] = pd.to_datetime(df['SettlementDate'], errors='coerce', format='%d-%b-%Y')

    # --- TransactionType and Security Parsing ---
    df['TransactionType'] = 'Unknown'
    df['Security'] = None
    df['Quantity'] = None # Placeholder for now
    df['Price'] = None # Placeholder for now
    df['BrokerageFee'] = None # Placeholder for now

    # AccountId processing (existing logic)
    if 'AccountId' not in df.columns or df['AccountId'].isnull().all():
        match = re.search(r'(\d+)INET', sheet_name)
        if match:
            df['AccountId'] = match.group(1)
        else:
            # Fallback, perhaps extract from filename
            df['AccountId'] = input_file_path.split('_')[-2] # e.g., '16518125' from filename
    
    # TransactionText (now standardized) based parsing - ORDER MATTERS!
    # Specific fees/interest first
    df.loc[df['TransactionText'].str.contains('Custody Fee|Depotgebyr', na=False, flags=re.IGNORECASE), 'TransactionType'] = 'Fee'
    df.loc[df['TransactionText'].str.contains('Interest|Rente', na=False, flags=re.IGNORECASE), 'TransactionType'] = 'Interest'

    # CFD specific handling - removed capturing groups from str.contains
    cfd_finance_mask = df['TransactionText'].str.contains('CFD Finance', na=False) & (df['TransactionType'] == 'Unknown')
    df.loc[cfd_finance_mask, 'TransactionType'] = 'CFD_Fee'

    # Changed `str.contains` pattern to not have capturing groups
    cfd_trade_mask = df['TransactionText'].str.contains(r'CFDs\s+[A-Z0-9.:]+', na=False, flags=re.IGNORECASE) & (df['TransactionType'] == 'Unknown')
    df.loc[cfd_trade_mask, 'TransactionType'] = 'CFD_Trade'
    df.loc[cfd_trade_mask, 'Security'] = df.loc[cfd_trade_mask, 'TransactionText'].str.extract(r'CFDs\s+([A-Z0-9.:]+)', flags=re.IGNORECASE, expand=False)

    # Withdrawals and Deposits
    df.loc[df['TransactionText'].str.contains('WITHDRAWAL|UTTAK', na=False, flags=re.IGNORECASE), 'TransactionType'] = 'Withdrawal'
    df.loc[df['TransactionText'].str.contains('DEPOSIT|INNSKUDD', na=False, flags=re.IGNORECASE), 'TransactionType'] = 'Deposit'
    
    # Corporate Actions
    df.loc[df['TransactionText'].str.contains('Corporate Actions|Selskapshendelser', na=False, flags=re.IGNORECASE), 'TransactionType'] = 'Corporate Action'

    # Handle 'Shares' for actual trades, but only for those not yet classified - removed capturing groups from str.contains
    trade_mask = df['TransactionText'].str.contains(r'(Shares|Aksjer)\s+[A-Z0-9.:]+', na=False, flags=re.IGNORECASE) & (df['TransactionType'] == 'Unknown')
    df.loc[trade_mask, 'TransactionType'] = 'Trade'
    
    # Extract security from both English and Norwegian 'Shares' patterns
    security_extracted = df.loc[trade_mask, 'TransactionText'].str.extract(r'(?:Shares|Aksjer)\s+([A-Z0-9.:]+)', flags=re.IGNORECASE, expand=False)
    df.loc[trade_mask, 'Security'] = security_extracted
    
    # Reorder and select relevant columns for consistency with Nordnet data
    final_cols = ['TradeDate', 'SettlementDate', 'TransactionType', 'Security', 'Amount',
                  'Quantity', 'Price', 'BrokerageFee', 'AccountId', 'CashBalance', 'TransactionText'] # Added CashBalance to final_cols
    
    # Ensure all final columns exist, fill missing with None/NaN if not from original data
    for col in final_cols:
        if col not in df.columns:
            df[col] = None
            
    # Reorder
    df = df[final_cols]
    
    return df

if __name__ == "__main__":
    for config in SAXO_FILES_CONFIG:
        input_file = config['input_file']
        sheet_name = config['sheet_name']
        output_file = config['output_file']

        print(f"\n--- Processing {os.path.basename(input_file)} ---")
        try:
            cleaned_df = clean_saxo_data(input_file, sheet_name, output_file)
            
            if not cleaned_df.empty:
                # Save the cleaned data
                cleaned_df.to_csv(output_file, index=False, encoding='utf-8')
                print(f"Cleaned Saxo data saved to {output_file}")
                
                print(f"\nCleaned Saxo DataFrame Info for {os.path.basename(input_file)}:")
                cleaned_df.info()
                print(f"\nCleaned Saxo DataFrame Head for {os.path.basename(input_file)}:")
                print(cleaned_df.head())
                print(f"\nCleaned Saxo DataFrame TransactionType counts for {os.path.basename(input_file)}:")
                print(cleaned_df['TransactionType'].value_counts())
            else:
                print(f"No data processed for {os.path.basename(input_file)}.")

        except FileNotFoundError:
            print(f"Error: Input file not found at {input_file}")
        except Exception as e:
            print(f"An error occurred while processing {input_file}: {e}")