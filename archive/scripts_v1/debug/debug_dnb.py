import sqlite3
import os

# Connect to DB relative to this script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
db_path = os.path.join(project_root, 'database', 'portfolio.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT GlobalID, Source, Type, Amount_Base, Currency_Base FROM transactions WHERE Type='BUY' AND Amount_Base > 0")
rows = c.fetchall()
print(f"Found {len(rows)} BUY transactions with positive Amount_Base:")
for row in rows:
    print(row)
conn.close()
