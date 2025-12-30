
import sqlite3

def normalize_all_to_nok():
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    
    print("Standardizing all transactions to NOK base...")
    
    # 1. Update Amount_Base for transactions where Currency_Base is not NOK
    # Logic: Amount_Base = Amount_Local * ExchangeRate (if local is the original)
    # Or if Local is NULL, use Amount_Base * ExchangeRate
    
    # First, let's find transactions where Currency_Base is USD/EUR and Amount_Base isn't converted yet.
    # We can detect this by checking if ABS(Amount_Base) is suspiciously close to ABS(Amount_Local)
    
    c.execute("""
        UPDATE transactions
        SET Amount_Base = Amount_Base * ExchangeRate,
            Currency_Base = 'NOK'
        WHERE Currency_Base IN ('USD', 'EUR', 'GBP')
        AND ExchangeRate IS NOT NULL
        AND ExchangeRate > 1.0
    """)
    
    print(f"Standardized {c.rowcount} transactions to NOK.")
    
    # 2. Cleanup: Ensure any remaining non-NOK labels are caught
    c.execute("UPDATE transactions SET Currency_Base = 'NOK' WHERE Currency_Base IS NULL")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    normalize_all_to_nok()
