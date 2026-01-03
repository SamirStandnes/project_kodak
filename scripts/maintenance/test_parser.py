import importlib
import sys
import os
import pandas as pd
from datetime import datetime

# Define the contract
REQUIRED_KEYS = {
    'external_id': str,
    'account_external_id': str,
    'isin': (str, type(None)), # Can be None
    'symbol': (str, type(None)),
    'date': str,
    'type': str,
    'quantity': (float, int),
    'price': (float, int),
    'amount': (float, int), # Asset Currency
    'currency': str,        # Asset Currency Code
    'amount_local': (float, int), # Base Currency
    'exchange_rate': (float, int),
    'description': str,
    'source_file': str,
    'fee': (float, int),
    'fee_currency': str,
    'fee_local': (float, int)
}

VALID_TYPES = [
    'BUY', 'SELL', 'DIVIDEND', 'DEPOSIT', 'WITHDRAWAL', 
    'INTEREST', 'FEE', 'TAX', 'CURRENCY_EXCHANGE', 
    'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT',
    'TILDELING INNLEGG RE', 'EMISJON INNLEGG VP'
]

def test_parser(parser_name, file_path):
    print(f"--- TESTING PARSER: {parser_name} ---")
    print(f"Input File: {file_path}")
    
    # 1. Import
    try:
        module_name = f"scripts.pipeline.parsers.{parser_name}"
        parser = importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ FAIL: Could not import '{module_name}'. Error: {e}")
        return
    
    if not hasattr(parser, 'parse'):
        print(f"❌ FAIL: Module '{module_name}' has no 'parse' function.")
        return

    # 2. Run Parse
    try:
        results = parser.parse(file_path)
    except Exception as e:
        print(f"❌ FAIL: Parser crashed during execution. Error: {e}")
        return

    if not isinstance(results, list):
        print(f"❌ FAIL: Output must be a list, got {type(results)}.")
        return
    
    if not results:
        print("⚠️ WARNING: Parser returned empty list. Is the file empty or format unexpected?")
        return

    print(f"✅ Parser returned {len(results)} rows.")
    
    # 3. Validate Rows
    errors = 0
    
    for i, row in enumerate(results):
        row_err = []
        
        # Check Keys & Types
        for key, expected_type in REQUIRED_KEYS.items():
            if key not in row:
                row_err.append(f"Missing key: {key}")
                continue
            
            val = row[key]
            if not isinstance(val, expected_type):
                # Allow int/float flexibility
                if expected_type == (float, int) and isinstance(val, (float, int)):
                    continue
                row_err.append(f"Key '{key}' has wrong type {type(val)}. Expected {expected_type}")

        # Check Logic
        if 'type' in row and row['type'] not in VALID_TYPES:
            row_err.append(f"Invalid Type: '{row['type']}'")
            
        if 'currency' in row and len(str(row['currency'])) != 3:
             row_err.append(f"Invalid Currency code: '{row['currency']}'")

        # Check Math (Roughly)
        if 'amount' in row and 'amount_local' in row and 'exchange_rate' in row:
            amt = row['amount']
            local = row['amount_local']
            rate = row['exchange_rate']
            
            if rate > 0 and amt != 0:
                calc_local = amt * rate
                # Allow tiny rounding diff
                if abs(calc_local - local) > 1.0: # 1.0 unit tolerance
                    row_err.append(f"Math Mismatch: {amt} * {rate} = {calc_local:.2f}, but got {local}")

        if row_err:
            print(f"❌ Row {i} Errors: {'; '.join(row_err)}")
            errors += 1
            if errors > 5:
                print("... Stopping after 5 faulty rows.")
                break
    
    if errors == 0:
        print("\n🎉 SUCCESS: All checks passed! This parser is standard-compliant.")
    else:
        print(f"\n❌ FAILED: Found errors in {errors} rows.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.maintenance.test_parser <parser_name> <sample_file_path>")
        print("Example: python -m scripts.maintenance.test_parser nordnet data/new_raw_transactions/nordnet/sample.csv")
    else:
        test_parser(sys.argv[1], sys.argv[2])
