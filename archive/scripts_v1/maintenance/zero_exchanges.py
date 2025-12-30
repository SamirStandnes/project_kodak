
import sqlite3

def zero_out_exchanges():
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    
    print("Zeroing out Amount_Base for CURRENCY_EXCHANGE to prevent double-counting cash...")
    
    c.execute("UPDATE transactions SET Amount_Base = 0 WHERE Type = 'CURRENCY_EXCHANGE'")
    print(f"Zeroed out {c.rowcount} currency exchange legs.")
    
    # Also, ADJUSTMENTS are often used for internal movements or corrections.
    # If they have a large positive sum, they might be inflating cash too.
    # Let's check them.
    c.execute("SELECT SUM(Amount_Base) FROM transactions WHERE Type = 'ADJUSTMENT'")
    adj_sum = c.fetchone()[0]
    print(f"Current sum of ADJUSTMENTS: {adj_sum}")
    
    # If adjustments are positive, they are likely missing their 'outflow' leg.
    # For now, let's keep them but be aware.
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    zero_out_exchanges()
