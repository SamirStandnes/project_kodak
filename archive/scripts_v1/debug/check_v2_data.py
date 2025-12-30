
import sqlite3
import pandas as pd

def check_v2_data():
    conn = sqlite3.connect('database/portfolio.db')
    # Look at a few US trades
    df = pd.read_sql_query("""
        SELECT Symbol, TradeDate, Type, Category, Amount_Raw, Currency_Raw, Amount_NOK 
        FROM transactions_v2 
        WHERE Symbol LIKE '%Alphabet%' OR Symbol LIKE '%Amazon%'
        LIMIT 10
    """, conn)
    print(df)
    conn.close()

if __name__ == '__main__':
    check_v2_data()
