from scripts.shared.db import execute_query
import pandas as pd

def check_hkd_rate():
    query = """
        SELECT date, exchange_rate 
        FROM transactions 
        WHERE currency = 'HKD' AND exchange_rate > 0
        ORDER BY ABS(strftime('%J', date) - strftime('%J', '2025-12-31'))
        LIMIT 5
    """
    results = execute_query(query)
    print("Nearest HKD Rates to 2025-12-31:")
    print(pd.DataFrame([dict(r) for r in results]))

if __name__ == "__main__":
    check_hkd_rate()
