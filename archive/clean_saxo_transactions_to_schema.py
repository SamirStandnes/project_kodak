import pandas as pd
import os
import re
import uuid
import numpy as np

def clean_saxo_transactions_to_schema(input_file_path, output_file_path):
    """
    Cleans and structures a SAXO Bank 'Transactions' Excel file and maps it to the unified portfolio schema.
    """
    print(f"Processing '{os.path.basename(input_file_path)}'...")
    
    # Read the first sheet, which is 'Transaksjoner'
    df = pd.read_excel(input_file_path, sheet_name='Transaksjoner')
    # --- 1. Rename columns to standardized English equivalents ---
    # Based on the latest exploration of 'Transaksjoner' sheet
    column_mapping = {
        'Kunde-ID': 'AccountID',
        'Handelsdato': 'TradeDate',
        'Valuteringsdato': 'SettlementDate',
        'Type': 'SaxoTransactionType', # This 'Type' column contains Kjøp/Salg/Utbytte etc.
        'Instrument': 'Symbol',
        'Instrument ISIN': 'ISIN',
        'Instrumentvaluta': 'Currency_Local', # This is the currency of the instrument/transaction
        'Bokført beløp': 'Amount_Local_Raw', # This is the monetary amount
        'Omregningskurs': 'ExchangeRate',
        # 'Antall' and 'Kurs' (Quantity and Price) are NOT in this file. This is a problem.
        # 'Hendelse' might be another description column, can be used for 'Description' later if needed
    }
    df = df.rename(columns=column_mapping)
    
        # Filter out rows that are not actual transactions (e.g., header/footer noise, empty rows)
        df = df.dropna(subset=['AccountID', 'TradeDate']).copy()
    
        # --- 2. Data Type Conversions ---
        df['TradeDate'] = pd.to_datetime(df['TradeDate'], errors='coerce')
        df['SettlementDate'] = pd.to_datetime(df['SettlementDate'], errors='coerce')
        # Since Quantity_Raw and Price_Raw are missing, we cannot convert them.
        # We will set Quantity and Price to 0.0 for now, as they are not available in this file.
        # This is a major limitation of this particular SAXO export file.
        df['Quantity'] = 0.0 
        df['Price'] = 0.0 
        df['Amount_Local_Raw'] = pd.to_numeric(df['Amount_Local_Raw'], errors='coerce').fillna(0)
        df['ExchangeRate'] = pd.to_numeric(df['ExchangeRate'], errors='coerce').fillna(1.0)
    
        # --- 3. Standardize Transaction Types and Quantities ---
        df['Type'] = 'Unknown'
        # df['Quantity'] is already 0.0
        # df['Price'] is already 0.0
        df['Amount_Local'] = df['Amount_Local_Raw'] # This will be adjusted for BUY/SELL signs
        df['Currency_Base'] = 'NOK' # Assuming NOK as the base currency
        # Initial calculation, Amount_Base for non-NOK local amounts. If Currency_Local is already NOK, ExchangeRate is 1.0.
        df['Amount_Base'] = df['Amount_Local_Raw'] * df['ExchangeRate']
    
        # Transaction Type Mapping and Quantity/Amount Signing
        for index, row in df.iterrows():
            saxo_type = str(row['SaxoTransactionType']).lower()
            
            if 'kjøp' in saxo_type:
                df.loc[index, 'Type'] = 'BUY'
                # Quantity remains 0.0 as it's not in this file
                df.loc[index, 'Amount_Local'] = -abs(row['Amount_Local_Raw']) # Cash out for BUY
                df.loc[index, 'Amount_Base'] = -abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'salg' in saxo_type:
                df.loc[index, 'Type'] = 'SELL'
                # Quantity remains 0.0 as it's not in this file
                df.loc[index, 'Amount_Local'] = abs(row['Amount_Local_Raw']) # Cash in for SELL
                df.loc[index, 'Amount_Base'] = abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'utbytte' in saxo_type:
                df.loc[index, 'Type'] = 'DIVIDEND'
                df.loc[index, 'Amount_Local'] = abs(row['Amount_Local_Raw']) # Cash in
                df.loc[index, 'Amount_Base'] = abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'gebyr' in saxo_type or 'fee' in saxo_type:
                df.loc[index, 'Type'] = 'FEE'
                df.loc[index, 'Amount_Local'] = -abs(row['Amount_Local_Raw']) # Fees are cash out
                df.loc[index, 'Amount_Base'] = -abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'rente' in saxo_type or 'interest' in saxo_type:
                df.loc[index, 'Type'] = 'INTEREST'
                df.loc[index, 'Amount_Local'] = abs(row['Amount_Local_Raw']) # Cash in
                df.loc[index, 'Amount_Base'] = abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'innskudd' in saxo_type or 'deposit' in saxo_type:
                df.loc[index, 'Type'] = 'DEPOSIT'
                df.loc[index, 'Amount_Local'] = abs(row['Amount_Local_Raw'])
                df.loc[index, 'Amount_Base'] = abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            elif 'uttak' in saxo_type or 'withdrawal' in saxo_type:
                df.loc[index, 'Type'] = 'WITHDRAWAL'
                df.loc[index, 'Amount_Local'] = -abs(row['Amount_Local_Raw'])
                df.loc[index, 'Amount_Base'] = -abs(row['Amount_Local_Raw'] * row['ExchangeRate'])
            else:
                df.loc[index, 'Type'] = 'ADJUSTMENT' # Fallback for unknown types
                df.loc[index, 'Amount_Local'] = row['Amount_Local_Raw']
                df.loc[index, 'Amount_Base'] = row['Amount_Local_Raw'] * row['ExchangeRate']
                # Quantity for adjustments remains 0.0 as it's not in this file
    


    # --- 4. Final Schema Mapping ---
    df['GlobalID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    df['Source'] = 'SAXO'
    df['OriginalID'] = None # No clear original ID, can use a combination if needed
    df['ParentID'] = None # No fee linking logic yet
    df['Description'] = df['SaxoTransactionType'] # Use original type as description for context
    
    # Select and Reorder columns to match the main schema
    columns_order = [
        'GlobalID', 'Source', 'AccountID', 'OriginalID', 'ParentID',
        'TradeDate', 'SettlementDate', 'Type', 'Symbol', 'ISIN', 
        'Description', 'Quantity', 'Price', 
        'Amount_Base', 'Currency_Base', 
        'Amount_Local', 'Currency_Local', 
        'ExchangeRate'
    ]
    df_out = df[columns_order]

    # Save to the specified excel file
    df_out.to_excel(output_file_path, index=False)
    print(f"\nCleaned SAXO transaction data saved to {output_file_path}")
    
    # Display results for verification
    print("\n--- First 5 rows of cleaned SAXO transaction data ---")
    print(df_out.head().to_markdown(index=False))


if __name__ == "__main__":
    saxo_transactions_file = {
        'input_file': r"C:\Users\Samir\project-kodak\data\Transactions_19269921_2024-11-07_2025-12-11.xlsx",
        'output_file': 'saxo_transactions_schema.xlsx'
    }

    clean_saxo_transactions_to_schema(saxo_transactions_file['input_file'], saxo_transactions_file['output_file'])
