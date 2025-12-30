import sqlite3
import pandas as pd
def check_googl_v2():
    conn = sqlite3.connect('database/portfolio.db')
    query = "SELECT TradeDate, Type, Quantity, Amount_NOK, Description FROM transactions WHERE Symbol LIKE '%Alphabet%' OR Symbol LIKE 'GOOGL' ORDER BY TradeDate"
    df = pd.read_sql_query(query, conn)
    print(df)
    print(f"\nTOTAL QUANTITY: {df['Quantity'].sum()}")
    conn.close()
check_googl_v2()
