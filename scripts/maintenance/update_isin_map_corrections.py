
import sqlite3

db_path = 'database/portfolio.db'

def update_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Updating InstrumentType, Country, and Sector...")

    # 1. specific ISIN mappings (ISIN -> (Country, Sector, InstrumentType))
    updates = {
        # The specific Ireland ETFs you mentioned
        'IE00BYZK4552': ('Global', 'Technology', 'ETF'),      # RBOT
        'IE00B4L5Y983': ('Global', 'Broad Market', 'ETF'),    # EUNL
        'IE00BL25JM42': ('Global', 'Broad Market', 'ETF'),    # XDEV
        'IE00BYZK4776': ('Global', 'Healthcare', 'ETF'),      # HEAL
        
        # Other ETFs/Funds likely needing correction from 'ETF' sector
        'IE00B4QNHZ41': ('Europe', 'Broad Market', 'ETF'),    # DES2 (Europe SmallCap)
        'US46138W1071': ('Global', 'Currency', 'ETF'),        # FXY (Yen Trust)
        'US4642851053': ('Global', 'Precious Metals', 'ETF'), # IAU (Gold)
        'US4642852044': ('Global', 'Precious Metals', 'ETF'), # IAU (Duplicate/Different share class?)
        'US46141D2036': ('United States', 'Currency', 'ETF'), # UUP (USD Bullish)
        'US97717W4713': ('United States', 'Currency', 'ETF'), # USDU (USD)
        'US46140H4039': ('Global', 'Commodities', 'ETF'),     # DBO (Oil)
        'US92189F6016': ('Global', 'Energy', 'ETF'),          # NLR (Nuclear)
        'US5007676787': ('Global', 'Commodities', 'ETF'),     # KRBN (Carbon)
        'SE0009723026': ('Norway', 'Broad Market', 'ETF'),    # OBXX (OBX Index)
        
        # Funds
        'SE0005993110': ('Norway', 'Broad Market', 'Fund'),   # NN-NORGE-IN.OL (Index Fund)
    }

    for isin, (country, sector, instrument_type) in updates.items():
        print(f"Updating {isin}: Country={country}, Sector={sector}, Type={instrument_type}")
        cursor.execute("""
            UPDATE isin_symbol_map 
            SET Country = ?, Sector = ?, InstrumentType = ? 
            WHERE ISIN = ?
        """, (country, sector, instrument_type, isin))

    # 2. General Rules
    
    # Set InstrumentType to 'ETF' where Sector WAS 'ETF' (for any we missed in specific map)
    # But first we rely on the specific map.
    # Let's set a default 'Equity' for anything that hasn't been set yet.
    
    print("Setting default InstrumentType to 'Equity' for remaining records...")
    cursor.execute("""
        UPDATE isin_symbol_map 
        SET InstrumentType = 'Equity' 
        WHERE InstrumentType IS NULL
    """,)

    conn.commit()
    print("Update complete.")
    
    # Verify
    print("\n--- Updated Data (Top 30) ---")
    cursor.execute("SELECT ISIN, Symbol, Country, Sector, InstrumentType FROM isin_symbol_map")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    conn.close()

if __name__ == "__main__":
    update_database()
