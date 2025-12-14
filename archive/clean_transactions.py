import pandas as pd
import os

# --- Configuration ---
INPUT_FILE_PATH = os.path.join('data', 'transactions-and-notes-export.csv')
OUTPUT_FILE_PATH = os.path.join('data', 'cleaned_transactions.csv')

# --- Column Name Translation ---
COLUMN_TRANSLATIONS = {
    'Id': 'Id',
    'Bokføringsdag': 'BookingDate',
    'Handelsdag': 'TradeDate',
    'Oppgjørsdag': 'SettlementDate',
    'Portefølje': 'Portfolio',
    'Transaksjonstype': 'TransactionType',
    'Verdipapir': 'Security',
    'ISIN': 'ISIN',
    'Antall': 'Quantity',
    'Kurs': 'Price',
    'Rente': 'Interest',
    'Totale Avgifter': 'TotalFees',
    'Valuta': 'Currency',
    'Beløp': 'Amount',
    'Valuta.1': 'Currency1',
    'Kjøpsverdi': 'PurchaseValue',
    'Valuta.2': 'Currency2',
    'Resultat': 'Result',
    'Valuta.3': 'Currency3',
    'Totalt antall': 'TotalQuantity',
    'Saldo': 'Balance',
    'Vekslingskurs': 'ExchangeRate',
    'Transaksjonstekst': 'TransactionText',
    'Makuleringsdato': 'CancellationDate',
    'Sluttseddelnummer': 'TradeNoteNumber',
    'Verifikationsnummer': 'VerificationNumber',
    'Kurtasje': 'BrokerageFee',
    'Valuta.4': 'Currency4',
    'Valutakurs': 'FxRate',
    'Innledende rente': 'InitialInterest'
}

# --- Data Cleaning Functions ---
def to_numeric_with_comma(series):
    """Converts a pandas Series with comma decimals to numeric."""
    return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce')

def clean_data(df):
    """Cleans the Nordnet transaction DataFrame."""
    # 1. Rename columns
    df = df.rename(columns=COLUMN_TRANSLATIONS)

    # 2. Convert date columns
    date_cols = ['BookingDate', 'TradeDate', 'SettlementDate']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # 3. Convert numeric columns
    numeric_cols = [
        'Quantity', 'Price', 'TotalFees', 'Amount',
        'PurchaseValue', 'Result', 'TotalQuantity',
        'Balance', 'ExchangeRate', 'BrokerageFee', 'FxRate'
    ]
    for col in numeric_cols:
        df[col] = to_numeric_with_comma(df[col])

    # 4. Drop fully empty columns identified from exploration
    df = df.drop(columns=['CancellationDate', 'InitialInterest'])

    # 5. Fill NaN values in 'Currency' with 'NOK' for Nordnet data
    if 'Currency' in df.columns:
        df['Currency'] = df['Currency'].fillna('NOK')

    return df

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Reading data from {INPUT_FILE_PATH}...")
    try:
        # Load the raw data
        raw_df = pd.read_csv(INPUT_FILE_PATH, delimiter='\t', encoding='utf-16')

        # Clean the data
        print("Cleaning data (translating headers, converting types, filling missing currency)...")
        cleaned_df = clean_data(raw_df.copy())

        # Save the cleaned data
        cleaned_df.to_csv(OUTPUT_FILE_PATH, index=False, encoding='utf-8')
        print(f"Cleaned data saved to {OUTPUT_FILE_PATH}")

        # Display info of the cleaned dataframe
        print("\nCleaned DataFrame Info:")
        cleaned_df.info()

    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_FILE_PATH}")
    except Exception as e:
        print(f"An error occurred: {e}")