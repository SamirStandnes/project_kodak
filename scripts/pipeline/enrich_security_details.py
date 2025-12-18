import sqlite3
import yfinance as yf
import pandas as pd

# Basic mapping of country to region
COUNTRY_TO_REGION = {
    'United States': 'North America',
    'Canada': 'North America',
    'Norway': 'Europe',
    'Sweden': 'Europe',
    'Denmark': 'Europe',
    'Finland': 'Europe',
    'United Kingdom': 'Europe',
    'Germany': 'Europe',
    'France': 'Europe',
    'Netherlands': 'Europe',
    'Switzerland': 'Europe',
    'Ireland': 'Europe',
    'Luxembourg': 'Europe',
    'China': 'Asia',
    'Japan': 'Asia',
    'Hong Kong': 'Asia',
    'India': 'Asia',
    'South Korea': 'Asia',
    'Taiwan': 'Asia',
    'Australia': 'Oceania',
    'New Zealand': 'Oceania'
}

def get_country_region(country):
    """Derives a region from a country."""
    if country in COUNTRY_TO_REGION:
        return COUNTRY_TO_REGION[country]
    return 'Other'

def enrich_security_details():
    """
    Fetches details for each security using yfinance and populates
    Sector, Region, and Country in the isin_symbol_map table.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    # Use a dictionary cursor to easily access columns by name
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all securities that haven't been enriched yet
    c.execute("SELECT ISIN, Symbol FROM isin_symbol_map WHERE Sector IS NULL OR Country IS NULL")
    securities_to_enrich = c.fetchall()

    if not securities_to_enrich:
        print("All securities are already enriched with Sector and Country details.")
        conn.close()
        return

    print(f"Found {len(securities_to_enrich)} securities to enrich...")

    for security in securities_to_enrich:
        isin = security['ISIN']
        symbol_str = security['Symbol']
        
        print(f"Fetching details for {symbol_str} ({isin})...")
        
        try:
            # yfinance can be sensitive to the ticker format, e.g., on Oslo Børs
            if '.OL' not in symbol_str and 'OBX' not in symbol_str and 'OSE' in symbol_str:
                 # Attempt to fix common Norwegian ticker issue
                 # This is a heuristic and might need refinement
                 ticker_obj = yf.Ticker(f"{symbol_str}.OL")
            else:
                 ticker_obj = yf.Ticker(symbol_str)

            info = ticker_obj.info

            sector = info.get('sector', 'N/A')
            country = info.get('country', 'N/A')
            region = get_country_region(country)
            
            # For some ETFs, 'sector' isn't available, but 'category' might be
            if sector == 'N/A' and 'category' in info:
                sector = info['category']

            if sector and country:
                print(f"  -> Found: Sector='{sector}', Country='{country}', Region='{region}'")
                c.execute('''
                    UPDATE isin_symbol_map
                    SET Sector = ?, Region = ?, Country = ?
                    WHERE ISIN = ?
                ''', (sector, region, country, isin))
            else:
                print(f"  -> Warning: Could not find full details for {symbol_str}.")

        except Exception as e:
            print(f"  -> Error fetching or processing data for {symbol_str}: {e}")
            # Optionally, mark as 'Error' to avoid retrying every time
            c.execute('''
                UPDATE isin_symbol_map
                SET Sector = 'Error', Region = 'Error', Country = 'Error'
                WHERE ISIN = ?
            ''', (isin,))
    
    conn.commit()
    conn.close()
    print("\nEnrichment process complete.")

if __name__ == '__main__':
    enrich_security_details()
