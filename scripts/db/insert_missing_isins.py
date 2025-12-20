
import sqlite3

db_path = 'database/portfolio.db'

def insert_missing_isins():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ISIN -> (Symbol, Currency, Country, Sector, InstrumentType)
    # Note: Currency is just a default, usually defined by the Symbol's exchange
    new_mappings = [
        ('NO0006222009', 'SPOG.OL', 'NOK', 'Norway', 'Financial Services', 'Equity'),
        ('NO0003053605', 'STB.OL', 'NOK', 'Norway', 'Financial Services', 'Equity'),
        ('NO0010096985', 'EQNR.OL', 'NOK', 'Norway', 'Energy', 'Equity'),
        ('US74347G4322', 'SQQQ', 'USD', 'United States', 'Technology', 'ETF'),
        ('US00214Q3020', 'ARKG', 'USD', 'Global', 'Healthcare', 'ETF'),
        ('US91232N2071', 'USO', 'USD', 'Global', 'Energy', 'ETF'),
        ('US46438F1012', 'IBIT', 'USD', 'Global', 'Cryptocurrency', 'ETF'),
        ('IE00BZCQB185', 'QDVE.DE', 'EUR', 'India', 'Broad Market', 'ETF'),
        ('US33616C1009', 'FRCB', 'USD', 'United States', 'Financial Services', 'Equity'),
        ('NO0010793961', 'N/A', 'NOK', 'Global', 'Precious Metals', 'Certificate'),
        ('NO0010848104', 'N/A', 'NOK', 'United States', 'Consumer Cyclical', 'Certificate'),
        ('NO0010847619', 'N/A', 'NOK', 'China', 'Consumer Cyclical', 'Certificate'),
        ('IE00BMTD2J60', 'N/A', 'NOK', 'Global', 'Broad Market', 'Fund'),
        ('IE00BMTD2X05', 'N/A', 'NOK', 'United States', 'Broad Market', 'Fund'),
        ('IE00BMTD2N07', 'N/A', 'NOK', 'Europe', 'Broad Market', 'Fund'),
        ('NO0013062323', 'N/A', 'NOK', 'Norway', 'N/A', 'Right'),
        ('NO0013642553', 'N/A', 'NOK', 'Norway', 'N/A', 'Right'),
    ]

    print("Inserting missing ISINs...")
    for isin, symbol, currency, country, sector, instrument_type in new_mappings:
        try:
            # Check if exists first to avoid Primary Key error if run multiple times
            cursor.execute("SELECT 1 FROM isin_symbol_map WHERE ISIN = ?", (isin,))
            if cursor.fetchone() is None:
                print(f"Adding {isin} ({symbol}) - {instrument_type}")
                cursor.execute("""
                    INSERT INTO isin_symbol_map (ISIN, Symbol, Currency, Country, Sector, InstrumentType)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (isin, symbol, currency, country, sector, instrument_type))
            else:
                print(f"Skipping {isin}, already exists.")
        except Exception as e:
            print(f"Error inserting {isin}: {e}")

    conn.commit()
    conn.close()
    print("Insertion complete.")

if __name__ == "__main__":
    insert_missing_isins()
