import sqlite3
import pandas as pd

def diagnose_sbo():
    conn = sqlite3.connect('database/portfolio.db')
    # Filter for SBO in 2021
    df = pd.read_sql_query("""
        SELECT Handelsdag, Transaksjonstype, Antall, Beløp, Transaksjonstekst 
        FROM raw_nordnet 
        WHERE Verdipapir LIKE '%Selvaag Bolig%'
        AND Handelsdag LIKE '2021%'
        ORDER BY Handelsdag
    """, conn)
    print(df)
    conn.close()

diagnose_sbo()
