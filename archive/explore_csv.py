
import pandas as pd
import os

# Define the file path
data_dir = 'data'
file_name = 'transactions-and-notes-export.csv'
file_path = os.path.join(data_dir, file_name)

print(f"Attempting to read file from: {file_path}")

try:
    # Read the tab-separated CSV file
    df = pd.read_csv(file_path, delimiter='\t', encoding='utf-16')

    # Display the first 5 rows
    print("\nFirst 5 rows of the DataFrame:")
    print(df.head())

    # Display a concise summary of the DataFrame
    print("\nDataFrame Info:")
    df.info()

except FileNotFoundError:
    print(f"Error: The file was not found at {file_path}")
except Exception as e:
    print(f"An error occurred: {e}")
