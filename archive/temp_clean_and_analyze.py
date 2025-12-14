import pandas as pd
import uuid
import numpy as np
import os

# --- Copied transform_nordnet_csv function from clean_nordnet_raw_data.py ---
def transform_nordnet_csv_temp(input_file, output_file):
    df = pd.read_csv(input_file, sep='\t', encoding='utf-16')

    def clean_num(val):
        if pd.isna(val) or val == '':
            return 0.0
        if isinstance(val, (float, int)):
            return float(val)
        val = str(val).replace(' ', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return 0.0

    df['Beløp_Clean'] = df['Beløp'].apply(clean_num)
    df['Kurtasje_Clean'] = df['Kurtasje'].apply(clean_num)
    df['Kjøpsverdi_Clean'] = df['Kjøpsverdi'].apply(clean_num)
    df['Kurs_Clean'] = df['Kurs'].apply(clean_num)
    df['Antall_Clean'] = df['Antall'].apply(clean_num)

    def classify_type(row):
        t_type = str(row['Transaksjonstype']).upper()
        text = str(row['Transaksjonstekst']).upper()
        
        if 'INTERNAL' in text:
            if 'INNSKUDD' in t_type:
                return 'TRANSFER_IN'
            if 'UTTAK' in t_type:
                return 'TRANSFER_OUT'
                
        if 'OVERFØRING' in t_type and 'INNSKUD' in t_type:
            return 'DEPOSIT'
        
        if 'ÖNSKAR TECKNA' in text:
            return 'ADJUSTMENT'
                
        mapping = {
            'KJØPT': 'BUY',
            'SALG': 'SELL',
            'UTBYTTE': 'DIVIDEND',
            'INNSKUDD': 'DEPOSIT',
            'UTTAK': 'WITHDRAWAL',
            'UTTAK INTERNET': 'WITHDRAWAL',
            'DEBETRENTE': 'INTEREST',
            'INNLØSN. UTTAK VP': 'SELL',
            'TILDELING INNLEGG RE': 'DEPOSIT',
            'AVG KORR': 'ADJUSTMENT',
            'TILBAKEBET. FOND AVG': 'DEPOSIT',
            'ERSTATNING': 'DEPOSIT',
            'SLETTING UTTAK VP': 'ADJUSTMENT',
            'EMISJON INNLEGG VP': 'DEPOSIT',
            'BYTTE INNLEGG VP': 'ADJUSTMENT',
            'BYTTE UTTAK VP': 'ADJUSTMENT',
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
        
        if 'RENTE' in t_type: return 'INTEREST'
        if 'SKATT' in t_type: return 'TAX'
        
        return t_type

    df['StandardizedType'] = df.apply(classify_type, axis=1)

    processed_rows = []

    for index, row in df.iterrows():
        base_id = row['Id']
        source = 'Nordnet'
        account_id = row['Portefølje']
        trade_date = row['Handelsdag']
        settle_date = row['Oppgjørsdag']
        symbol = row['Verdipapir']
        isin = row['ISIN']
        description = row['Transaksjonstekst'] if pd.notna(row['Transaksjonstekst']) else symbol
        
        amount_base = row['Beløp_Clean']
        curr_base = row['Valuta.1'] if pd.notna(row['Valuta.1']) else 'NOK'
        
        amount_local = row['Kjøpsverdi_Clean']
        curr_local = row['Valuta.2']
        
        if pd.isna(curr_local):
            if pd.notna(row['Valuta']) and pd.notna(row['ISIN']):
                 curr_local = row['Valuta']
                 if amount_local == 0 and row['Antall_Clean'] != 0:
                     amount_local = row['Kurs_Clean'] * row['Antall_Clean']
            else:
                 curr_local = curr_base
                 if amount_local == 0:
                     amount_local = abs(amount_base)

        # --- Quantity Handling (fixed) ---
        price = row['Kurs_Clean']
        t_type_upper = str(row['Transaksjonstype']).upper()

        if t_type_upper == 'BYTTE UTTAK VP':
            qty = -1 * abs(row['Antall_Clean'])
        elif t_type_upper == 'BYTTE INNLEGG VP':
            qty = abs(row['Antall_Clean'])
        elif row['StandardizedType'] in ['DIVIDEND', 'TAX', 'INTEREST', 'FEE', 'CURRENCY_EXCHANGE']:
            qty = 0
        elif row['StandardizedType'] == 'SELL':
            qty = -1 * abs(row['Antall_Clean'])
        elif row['StandardizedType'] == 'BUY':
            qty = abs(row['Antall_Clean'])
        else:
            qty = row['Antall_Clean']
        
        fee_val = row['Kurtasje_Clean']
        has_fee = (fee_val != 0 and not pd.isna(fee_val))
        
        main_row = {
            'GlobalID': str(uuid.uuid4()),
            'Source': source,
            'AccountID': account_id,
            'OriginalID': base_id,
            'ParentID': None,
            'TradeDate': trade_date,
            'SettlementDate': settle_date,
            'Type': row['StandardizedType'],
            'Symbol': symbol,
            'ISIN': isin,
            'Description': description,
            'Quantity': qty,
            'Price': price,
            'Amount_Base': amount_base,
            'Currency_Base': curr_base,
            'Amount_Local': amount_local,
            'Currency_Local': curr_local,
            'ExchangeRate': row['Vekslingskurs']
        }
        
        if has_fee:
            fee_amount_base = -1 * abs(fee_val)
            
            fee_row = main_row.copy()
            fee_row['GlobalID'] = str(uuid.uuid4())
            fee_row['Type'] = 'FEE'
            fee_row['ParentID'] = base_id
            fee_row['Quantity'] = 0
            fee_row['Price'] = 0
            fee_row['Amount_Base'] = fee_amount_base
            fee_row['Description'] = f"Fee for txn {base_id}"
            fee_row['Currency_Base'] = row['Valuta'] if pd.notna(row['Valuta']) else curr_base
            fee_row['Amount_Local'] = np.nan
            fee_row['Currency_Local'] = np.nan
            fee_row['ExchangeRate'] = np.nan
            
            main_row['Amount_Base'] = main_row['Amount_Base'] - fee_amount_base

            exchange_rate = clean_num(row['Vekslingskurs'])
            if curr_base != curr_local and exchange_rate != 0 and main_row['Amount_Local'] != 0:
                fee_in_local_currency = abs(fee_val) / exchange_rate
                main_row['Amount_Local'] = main_row['Amount_Local'] - fee_in_local_currency
            
            processed_rows.append(main_row)
            processed_rows.append(fee_row)
        else:
            processed_rows.append(main_row)

    df_out = pd.DataFrame(processed_rows)
    
    columns_order = [
        'GlobalID', 'Source', 'AccountID', 'OriginalID', 'ParentID',
        'TradeDate', 'SettlementDate', 'Type', 'Symbol', 'ISIN', 
        'Description', 'Quantity', 'Price', 
        'Amount_Base', 'Currency_Base', 
        'Amount_Local', 'Currency_Local', 
        'ExchangeRate'
    ]
    df_out = df_out[columns_order]
    
    df_out.to_excel(output_file, index=False)
    print(f"Temporary transformation complete. Saved to {output_file}")
    return df_out

# --- Copied analyze_account_portfolio logic from analyze_portfolio.py ---
def analyze_temp_portfolio(account_id, file_path, target_symbols):
    df = pd.read_excel(file_path)

    account_df = df[(df['AccountID'] == account_id) & (df['Type'] != 'FEE')].copy()

    if account_df.empty:
        print(f"No transactions found for AccountID: {account_id} (excluding fees) in {file_path}.")
        return

    # Filter for only the target symbols
    account_df = account_df[account_df['Symbol'].isin(target_symbols)].copy()

    if account_df.empty:
        print(f"No transactions for target symbols found for AccountID: {account_id} in {file_path}.")
        return

    portfolio_summary = account_df.groupby('ISIN').agg(
        Last_Symbol=('Symbol', 'last'),
        Net_Quantity=('Quantity', 'sum'),
        Net_Cash_Flow_Base_Currency=('Amount_Base', 'sum'),
        Last_Date=('SettlementDate', 'max')
    ).reset_index()

    portfolio_summary.rename(columns={'Last_Symbol': 'Symbol'}, inplace=True)

    threshold = 1e-6
    portfolio_summary = portfolio_summary[portfolio_summary['Net_Quantity'].abs() > threshold].copy()

    if portfolio_summary.empty:
        print(f"No open positions (Net Quantity != 0) for target symbols found for AccountID: {account_id} in {file_path}.")
        return

    portfolio_summary['Net_Cash_Flow_Base_Currency'] = portfolio_summary['Net_Cash_Flow_Base_Currency'].round(2)
    
    final_columns = ['Symbol', 'ISIN', 'Net_Quantity', 'Net_Cash_Flow_Base_Currency']
    portfolio_summary = portfolio_summary[final_columns]

    print(f"\nIndependent Test Summary for AccountID: {account_id} (from {os.path.basename(file_path)})")
    print(portfolio_summary.to_markdown(index=False))

if __name__ == "__main__":
    temp_output_dir = r"C:\Users\Samir\.gemini\tmp\a54b8b5e93412d26c0b837728763fc009144f6b411a3eaadf51341269a165282"
    temp_excel_file = os.path.join(temp_output_dir, "temp_portfolio_schema.xlsx")
    new_input_csv = "data/transactions-and-notes-export (1).csv"
    
    target_account_id = 24275430
    target_symbols_to_check = [
        'Nordnet Emerging Markets Indeks',
        'Nordnet Teknologi Indeks NOK'
    ]

    try:
        # Step 1: Process the new CSV into a temporary Excel file
        transform_nordnet_csv_temp(new_input_csv, temp_excel_file)
        
        # Step 2: Analyze the temporary Excel file
        analyze_temp_portfolio(target_account_id, temp_excel_file, target_symbols_to_check)
        
    finally:
        # Step 3: Clean up the temporary Excel file
        if os.path.exists(temp_excel_file):
            os.remove(temp_excel_file)
            print(f"\nCleaned up temporary file: {temp_excel_file}")
