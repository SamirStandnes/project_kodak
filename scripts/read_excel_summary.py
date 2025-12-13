import pandas as pd

try:
    df = pd.read_excel('portfolio_schema.xlsx')
    print("First 5 rows of portfolio_schema.xlsx:")
    print(df.head().to_markdown(index=False))
    print("\nColumns in portfolio_schema.xlsx:")
    # Print columns directly
    for col in df.columns:
        print(col)
except Exception as e:
    print(f"Error reading Excel file: {e}")