
import sqlite3

db_path = 'database/portfolio.db'

def update_etf_symbols():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ISIN -> New Symbol
    updates = {
        'IE00B4L5Y983': 'EUNL.DE',      # iShares Core MSCI World
        'IE00BL25JM42': 'XDEV.DE',      # Xtrackers MSCI World Value
        'SE0009723026': 'XACT-OBX.OL',  # XACT OBX (previously OBXX)
        'NO0010612450': 'SBO.OL',       # Selvaag Bolig (previously SBO)
    }

    print("Updating ETF and Equity symbols for Yahoo Finance compatibility...")
    for isin, symbol in updates.items():
        print(f"Updating {isin} to Symbol: {symbol}")
        cursor.execute("UPDATE isin_symbol_map SET Symbol = ? WHERE ISIN = ?", (symbol, isin))

    conn.commit()
    conn.close()
    print("Update complete.")

if __name__ == "__main__":
    update_etf_symbols()
