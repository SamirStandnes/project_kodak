import pandas as pd
import uuid
import numpy as np

def transform_nordnet_csv(input_file, output_file='data/processed/nordnet_cleaned.xlsx'):
    # Load the file (assuming tab delimiter based on your file)
    df = pd.read_csv(input_file, sep='\t', encoding='utf-16')

    # --- Helper: Clean Currency Strings (e.g., "1 200,50") ---
    def clean_num(val):
        if pd.isna(val) or val == '':
            return 0.0
        if isinstance(val, (float, int)):
            return float(val)
        # Remove spaces, replace comma with dot
        val = str(val).replace(' ', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return 0.0

    # Apply cleaning to numerical columns
    df['Beløp_Clean'] = df['Beløp'].apply(clean_num)
    df['Kurtasje_Clean'] = df['Kurtasje'].apply(clean_num)
    df['Kjøpsverdi_Clean'] = df['Kjøpsverdi'].apply(clean_num)
    df['Kurs_Clean'] = df['Kurs'].apply(clean_num)
    df['Antall_Clean'] = df['Antall'].apply(clean_num)

    # --- Logic: Classify Transaction Types ---
    def classify_type(row):
        t_type = str(row['Transaksjonstype']).upper()
        text = str(row['Transaksjonstekst']).upper()
        
        # Check for Internal Transfers first
        if 'INTERNAL' in text:
            if 'INNSKUDD' in t_type:
                return 'TRANSFER_IN'
            if 'UTTAK' in t_type:
                return 'TRANSFER_OUT'
                
        # Handle "Overføring innskud Trustly"
        if 'OVERFØRING' in t_type and 'INNSKUD' in t_type:
            return 'DEPOSIT'
        
        # Handle share application as adjustment
        if 'ÖNSKAR TECKNA' in text:
            return 'ADJUSTMENT'
                
        # Standard Mappings
        mapping = {
            'KJØPT': 'BUY',
            'SALG': 'SELL',
            'UTBYTTE': 'DIVIDEND',
            'INNSKUDD': 'DEPOSIT',
            'UTTAK': 'WITHDRAWAL',
            'UTTAK INTERNET': 'WITHDRAWAL',
            'DEBETRENTE': 'INTEREST',
            # Additional Nordnet specific mappings
            'INNLØSN. UTTAK VP': 'SELL', # Redemption Withdrawal Securities -> Sell
            'TILDELING INNLEGG RE': 'DEPOSIT', # Allocation Entry -> Deposit
            'AVG KORR': 'ADJUSTMENT', # Average Correction -> Adjustment
            'TILBAKEBET. FOND AVG': 'DEPOSIT', # Repayment Fund Average -> Deposit
            'ERSTATNING': 'DEPOSIT', # Compensation -> Deposit
            'SLETTING UTTAK VP': 'ADJUSTMENT', # Deletion Withdrawal Securities -> Adjustment
            'EMISJON INNLEGG VP': 'DEPOSIT', # Issuance Entry Securities -> Deposit
            'BYTTE INNLEGG VP': 'ADJUSTMENT', # Exchange Entry Securities -> Adjustment
            'BYTTE UTTAK VP': 'ADJUSTMENT', # Exchange Withdrawal Securities -> Adjustment
            # Mappings based on user feedback
            'OVERFØRING VIA TRUSTLY': 'DEPOSIT',
            'SALG VALUTA': 'CURRENCY_EXCHANGE',
            'KJØP VALUTA': 'CURRENCY_EXCHANGE',
            'INNSKUDD KONTANTER': 'DEPOSIT',
            'AVGIFT': 'FEE',
            'PLATTFORMAVGIFT': 'FEE',
            'UTSKILLING FISJON IN': 'DEPOSIT'
        }
        
        if t_type in mapping:
            return mapping[t_type]
        
        # Partial matches
        if 'RENTE' in t_type: return 'INTEREST'
        if 'SKATT' in t_type: return 'TAX'
        
        return t_type # Fallback to original if unknown

    df['StandardizedType'] = df.apply(classify_type, axis=1)

    processed_rows = []

    for index, row in df.iterrows():
        # --- 1. Extract Basic Info ---
        base_id = row['Id']
        source = 'Nordnet' # Hardcoded as per requirement
        account_id = row['Portefølje']
        trade_date = row['Handelsdag']
        settle_date = row['Oppgjørsdag']
        symbol = row['Verdipapir']
        isin = row['ISIN']
        description = row['Transaksjonstekst'] if pd.notna(row['Transaksjonstekst']) else symbol
        
        # --- 2. Handle Currencies ---
        # Base Currency (Account Currency)
        amount_base = row['Beløp_Clean']
        curr_base = row['Valuta.1'] if pd.notna(row['Valuta.1']) else 'NOK'
        
        # Local Currency (Asset Currency)
        # Logic: Use 'Valuta.2' (Currency of purchase value) if exists, else 'Valuta' (Currency of fees/price), else Base.
        amount_local = row['Kjøpsverdi_Clean']
        curr_local = row['Valuta.2']
        
        if pd.isna(curr_local):
            if pd.notna(row['Valuta']) and pd.notna(row['ISIN']):
                 curr_local = row['Valuta']
                 # Estimate local amount from price * quantity if purchase value is missing
                 if amount_local == 0 and row['Antall_Clean'] != 0:
                     amount_local = row['Kurs_Clean'] * row['Antall_Clean']
            else:
                 curr_local = curr_base
                 if amount_local == 0:
                     amount_local = abs(amount_base)

        # --- 3. Handle Quantities ---
        price = row['Kurs_Clean']
        t_type_upper = str(row['Transaksjonstype']).upper()

        # Logic to determine quantity based on transaction type
        if t_type_upper == 'BYTTE UTTAK VP':
            # Exchange withdrawal, quantity should be negative
            qty = -1 * abs(row['Antall_Clean'])
        elif t_type_upper == 'BYTTE INNLEGG VP':
            # Exchange deposit, quantity should be positive
            qty = abs(row['Antall_Clean'])
        elif row['StandardizedType'] in ['DIVIDEND', 'TAX', 'INTEREST', 'FEE', 'CURRENCY_EXCHANGE']:
            # Non-share transactions have zero quantity
            qty = 0
        elif row['StandardizedType'] == 'SELL':
            qty = -1 * abs(row['Antall_Clean'])
        elif row['StandardizedType'] == 'BUY':
            qty = abs(row['Antall_Clean'])
        else:
            # Default to the provided quantity for other types (e.g., DEPOSIT, ADJUSTMENT)
            qty = row['Antall_Clean']
        
        # --- 4. Fee Splitting Logic ---
        fee_val = row['Kurtasje_Clean']
        has_fee = (fee_val != 0 and not pd.isna(fee_val))
        
        # Create the MAIN transaction row
        main_row = {
            'GlobalID': str(uuid.uuid4()),
            'Source': source,
            'AccountID': account_id,
            'OriginalID': base_id,
            'ParentID': None, # Main row has no parent
            'TradeDate': trade_date,
            'SettlementDate': settle_date,
            'Type': row['StandardizedType'],
            'Symbol': symbol,
            'ISIN': isin,
            'Description': description,
            'Quantity': qty,
            'Price': price,
            'Amount_Base': amount_base, # Will be adjusted if fee exists
            'Currency_Base': curr_base,
            'Amount_Local': amount_local,
            'Currency_Local': curr_local,
            'ExchangeRate': row['Vekslingskurs']
        }
        
        if has_fee:
            # FEE ROW creation
            # Fee is a cost, so Amount should be negative. Nordnet usually reports it positive in the 'Kurtasje' column.
            fee_amount_base = -1 * abs(fee_val)
            
            fee_row = main_row.copy()
            fee_row['GlobalID'] = str(uuid.uuid4())
            fee_row['Type'] = 'FEE'
            fee_row['ParentID'] = base_id # Link to the main trade
            fee_row['Quantity'] = 0
            fee_row['Price'] = 0
            fee_row['Amount_Base'] = fee_amount_base
            fee_row['Description'] = f"Fee for txn {base_id}"
            # Fee currency is usually the base currency or the currency in 'Valuta' col
            fee_row['Currency_Base'] = row['Valuta'] if pd.notna(row['Valuta']) else curr_base
            fee_row['Amount_Local'] = np.nan
            fee_row['Currency_Local'] = np.nan
            fee_row['ExchangeRate'] = np.nan
            
            # ADJUST MAIN ROW
            # We must add the fee back to the Amount to get "Gross Amount".
            # If we spent 1000 (Amount -1000) and 10 was fee, the Asset cost was 990.
            # So: -1000 - (-10) = -990.
            main_row['Amount_Base'] = main_row['Amount_Base'] - fee_amount_base

            # For foreign currency trades, adjust the local amount which also includes the fee.
            exchange_rate = clean_num(row['Vekslingskurs'])
            if curr_base != curr_local and exchange_rate != 0 and main_row['Amount_Local'] != 0:
                # fee_val is the positive fee amount in base currency. Convert it to local.
                fee_in_local_currency = abs(fee_val) / exchange_rate
                # Amount_Local is the gross value, so subtract the fee to get the net asset value.
                # This applies to both BUY (where Amount_Local is positive) and SELL (also positive).
                main_row['Amount_Local'] = main_row['Amount_Local'] - fee_in_local_currency
            
            processed_rows.append(main_row)
            processed_rows.append(fee_row)
        else:
            processed_rows.append(main_row)

    # --- Create DataFrame and Save ---
    df_out = pd.DataFrame(processed_rows)
    
    # Select and Reorder columns
    columns_order = [
        'GlobalID', 'Source', 'AccountID', 'OriginalID', 'ParentID',
        'TradeDate', 'SettlementDate', 'Type', 'Symbol', 'ISIN', 
        'Description', 'Quantity', 'Price', 
        'Amount_Base', 'Currency_Base', 
        'Amount_Local', 'Currency_Local', 
        'ExchangeRate'
    ]
    df_out = df_out[columns_order]
    
    # Save
    df_out.to_excel(output_file, index=False)
    print(f"Transformation complete. Saved to {output_file}")
    return df_out

# Run the function
if __name__ == "__main__":
    # This is for standalone execution from the project root.
    transform_nordnet_csv('data/raw/transactions-and-notes-export.csv', 'data/processed/nordnet_cleaned.xlsx')
