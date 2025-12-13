import sqlite3

def get_unpriced_securities():
    """
    Gets the ISIN and description for currently held securities that are not in the current_prices table.
    """
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    c.execute('''
        SELECT T.ISIN, T.Description
        FROM transactions T
        LEFT JOIN current_prices CP ON T.ISIN = CP.ISIN
        WHERE T.ISIN IN (
            SELECT ISIN
            FROM transactions
            WHERE ISIN IS NOT NULL
            GROUP BY ISIN
            HAVING SUM(Quantity) > 0
        ) AND CP.ISIN IS NULL
        GROUP BY T.ISIN
    ''')
    unpriced_securities = c.fetchall()
    conn.close()
    return unpriced_securities

if __name__ == '__main__':
    unpriced = get_unpriced_securities()
    if unpriced:
        print("We could not fetch prices for the following securities:")
        for isin, description in unpriced:
            print(f"  - {description} ({isin})")
    else:
        print("All current holdings have a fetched price.")
