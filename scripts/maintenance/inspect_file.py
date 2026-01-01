import pandas as pd
import sys
import os

def inspect_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"--- ANALYZING: {os.path.basename(file_path)} ---")
    
    # 1. Try to load file
    try:
        if file_path.endswith('.csv'):
            # Try different separators
            try:
                df = pd.read_csv(file_path)
                if len(df.columns) <= 1: # Likely wrong separator
                    df = pd.read_csv(file_path, sep=';')
                if len(df.columns) <= 1:
                    df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
            except:
                df = pd.read_csv(file_path, sep=None, engine='python')
                
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            print("Unsupported format. Use .csv or .xlsx")
            return
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    # 2. Print Summary for the AI
    print("\n[INSTRUCTIONS FOR AI]")
    print(f"I have a file named '{os.path.basename(file_path)}'.")
    print("Here are the columns and the first 3 rows of data:\n")
    
    # Set display options to ensure data isn't hidden
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', 5)
    pd.set_option('display.width', 1000)
    
    print(df.head(3).to_markdown(index=False))
    
    print("\n[COLUMN TYPES]")
    print(df.dtypes)
    
    print("\n--- END OF REPORT ---")
    print("\nNow, copy the section above and paste it into your AI prompt along with the 'Standard Schema' requirements.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.maintenance.inspect_file <path_to_file>")
    else:
        inspect_file(sys.argv[1])
