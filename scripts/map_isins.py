import sqlite3

def get_all_holdings():
    """
    Gets the ISIN and description for all currently held securities.
    """
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    c.execute('''
        SELECT ISIN, Description
        FROM transactions
        WHERE ISIN IN (
            SELECT ISIN
            FROM transactions
            WHERE ISIN IS NOT NULL
            GROUP BY ISIN
            HAVING SUM(Quantity) > 0
        )
        GROUP BY ISIN
    ''')
    all_holdings = c.fetchall()
    conn.close()
    return all_holdings

def get_existing_mapping(isin):
    """
    Gets the existing symbol and currency for a given ISIN from the mapping table.
    """
    conn = sqlite3.connect('database/portfolio.db')
    c = conn.cursor()
    c.execute('SELECT Symbol, Currency FROM isin_symbol_map WHERE ISIN = ?', (isin,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None)

def map_isins_and_currencies():
    """
    Prompts the user to map ISINs to ticker symbols and currencies,
    and stores the mapping in the database.
    """
    all_holdings = get_all_holdings()

    if not all_holdings:
        print("No current holdings to map.")
        return

    print("Please provide the ticker symbol and currency for the following securities.")
    print("Press Enter to keep the existing value if one is shown.")

    mappings = []
    for isin, description in all_holdings:
        existing_symbol, existing_currency = get_existing_mapping(isin)
        
        # Prompt for symbol
        symbol_prompt = f"  - {description} ({isin})\n    Symbol"
        if existing_symbol:
            symbol_prompt += f" [current: {existing_symbol}]: "
        else:
            symbol_prompt += ": "
        new_symbol = input(symbol_prompt).strip()
        final_symbol = new_symbol if new_symbol else existing_symbol

        # Prompt for currency
        currency_prompt = f"    Currency"
        if existing_currency:
            currency_prompt += f" [current: {existing_currency}]: "
        else:
            currency_prompt += ": "
        new_currency = input(currency_prompt).strip().upper()
        final_currency = new_currency if new_currency else existing_currency
        
        if final_symbol and final_currency:
            mappings.append((isin, final_symbol, final_currency))

    if mappings:
        conn = sqlite3.connect('database/portfolio.db')
        c = conn.cursor()
        c.executemany('REPLACE INTO isin_symbol_map (ISIN, Symbol, Currency) VALUES (?, ?, ?)', mappings)
        conn.commit()
        conn.close()
        print("\nMappings stored successfully.")

if __name__ == '__main__':
    map_isins_and_currencies()
