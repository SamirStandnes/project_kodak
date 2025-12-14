import pandas as pd
import sys

def explore_excel_file(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        if not sheet_names:
            print("No sheets found in the Excel file. It may be empty or corrupt.")
            return

        print(f"Available sheets: {sheet_names}")

        target_sheet = 'Transaksjoner'
        
        if target_sheet in sheet_names:
            print(f"\n--- Raw DataFrame structure of first 50 rows from sheet: '{target_sheet}' ---")
            # Read the entire sheet as strings, with no header
            df_raw = pd.read_excel(file_path, sheet_name=target_sheet, header=None, dtype=str)
            # Print the first 50 rows, converting to a string representation
            print(df_raw.head(50))
        else:
            print(f"Target sheet '{target_sheet}' not found.")
            
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # The first file you provided
    target_file = r"C:\Users\Samir\project-kodak\data\Transactions_19269921_2024-11-07_2025-12-11.xlsx"
    explore_excel_file(target_file)
