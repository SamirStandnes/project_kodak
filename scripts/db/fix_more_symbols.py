
import sqlite3

db_path = 'database/portfolio.db'

def fix_more_symbols():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ISIN -> New Symbol
    updates = {
        'IE00BYZK4552': 'RBOT.L',      # iShares Automation & Robotics
        'IE00BYZK4776': 'HEAL.L',      # iShares Healthcare Innovation
    }

    print("Updating RBOT and HEAL to London tickers...")
    for isin, symbol in updates.items():
        cursor.execute("UPDATE isin_symbol_map SET Symbol = ? WHERE ISIN = ?", (symbol, isin))

    # Exclude the OBX ETF since Yahoo can't price it
    print("Excluding XACT OBX ETF (setting type to Fund)...")
    cursor.execute("UPDATE isin_symbol_map SET InstrumentType = 'Fund' WHERE ISIN = 'SE0009723026'")

    conn.commit()
    conn.close()
    print("Update complete.")

if __name__ == "__main__":
    fix_more_symbols()
