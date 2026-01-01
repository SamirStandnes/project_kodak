import yfinance as yf
import pandas as pd

def test_iau():
    # Dec 2020 and Dec 2021
    dates = ['2020-12-31', '2021-12-31']
    print("Testing IAU Prices (Raw vs Adjusted)")
    
    ticker = yf.Ticker("IAU")
    
    # Try different download methods
    df_raw = yf.download("IAU", start="2020-12-25", end="2022-01-05", auto_adjust=False)
    df_adj = yf.download("IAU", start="2020-12-25", end="2022-01-05", auto_adjust=True)
    
    for d in dates:
        print(f"\nTarget: {d}")
        try:
            ts = pd.Timestamp(d)
            p_raw = float(df_raw.loc[:ts].iloc[-1]['Close'])
            p_adj = float(df_adj.loc[:ts].iloc[-1]['Close'])
            actual_d = df_raw.loc[:ts].index[-1].strftime('%Y-%m-%d')
            print(f"  Actual:    {actual_d}")
            print(f"  Raw Close: {p_raw:.2f}")
            print(f"  Adj Close: {p_adj:.2f}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_iau()
