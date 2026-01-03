import yfinance as yf

def test_isin_lookup(isin):
    print(f"Testing ISIN: {isin}")
    try:
        t = yf.Ticker(isin)
        info = t.info
        if info and 'symbol' in info:
            print(f"  Found! Symbol: {info['symbol']}, Currency: {info.get('currency')}, Name: {info.get('longName')}")
        else:
            print("  No info found directly via Ticker(isin).")
    except Exception as e:
        print(f"  Error: {e}")

test_isin_lookup("US0378331005") # Apple
test_isin_lookup("CNE1000003X6") # Ping An
