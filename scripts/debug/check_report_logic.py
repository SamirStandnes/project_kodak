from scripts.shared.db import get_connection
import pandas as pd

def debug_report_query():
    conn = get_connection()
    # This is the exact query from get_yearly_contribution
    query = """
        SELECT t.date, i.symbol, i.currency 
        FROM transactions t 
        LEFT JOIN instruments i ON t.instrument_id = i.id 
        WHERE i.symbol = '2318.HK'
        LIMIT 1
    """
    df = pd.read_sql(query, conn)
    print(df)
    conn.close()

if __name__ == "__main__":
    debug_report_query()
