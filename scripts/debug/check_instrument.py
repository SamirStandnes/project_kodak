from scripts.shared.db import get_connection

conn = get_connection()
row = conn.execute("SELECT * FROM instruments WHERE symbol='DES2.DE'").fetchone()
conn.close()

if row:
    print(f"Symbol: {row['symbol']}")
    print(f"Name: {row['name']}")
    print(f"ISIN: {row['isin']}")
else:
    print("Instrument not found.")
