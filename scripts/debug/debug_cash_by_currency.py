import sqlite3
import pandas as pd
import os

# Connect to DB relative to this script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
db_path = os.path.join(project_root, 'database', 'portfolio.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT Currency_Base, SUM(Amount_Base) FROM transactions GROUP BY Currency_Base")
rows = c.fetchall()
print("Cash Balance by Currency (Raw):")
for currency, amount in rows:
    print(f"{currency}: {amount:,.2f}")
conn.close()
