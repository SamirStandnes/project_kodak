
import yfinance as yf
from datetime import datetime, timedelta

# Cache for exchange rates to avoid re-fetching
exchange_rates_cache = {}

def get_exchange_rate(base_currency, target_currency='NOK', date=None):
    """
    Gets the exchange rate for a given date.
    Uses a cache to avoid repeated API calls.
    If no date is provided, fetches the latest rate.
    """
    if not base_currency or base_currency == target_currency:
        return 1.0

    # Handle HKD conversion via USD cross-rate
    if base_currency == 'HKD' and target_currency == 'NOK':
        usd_nok_rate = get_exchange_rate('USD', 'NOK', date)
        hkd_usd_rate = get_exchange_rate('HKD', 'USD', date)
        if usd_nok_rate and hkd_usd_rate:
            return usd_nok_rate * hkd_usd_rate
        else:
            return None

    ticker = f"{base_currency}{target_currency}=X"
    # Use only the date part for caching historical rates
    date_str = date.split(' ')[0] if date else None
    cache_key = f"{ticker}-{date_str}" if date_str else ticker

    if cache_key in exchange_rates_cache:
        return exchange_rates_cache[cache_key]

    try:
        if date_str:
            # Fetch historical data for the given date
            start_date = date_str
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            rate_data = yf.Ticker(ticker).history(start=start_date, end=end_date)
        else:
            # Fetch the latest data
            rate_data = yf.Ticker(ticker).history(period="1d")
        
        if not rate_data.empty:
            rate = rate_data['Close'].iloc[0]
            exchange_rates_cache[cache_key] = rate
            return rate
        else:
            print(f"Warning: Could not fetch exchange rate for {ticker} on {date_str if date_str else 'latest'}")
            # Fallback for weekends/holidays: get the most recent previous day's rate
            if date_str:
                for i in range(1, 4): # Try up to 3 days before
                    prev_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
                    return get_exchange_rate(base_currency, target_currency, prev_date)
            return None
    except Exception as e:
        print(f"Warning: Error fetching rate for {ticker} on {date_str if date_str else 'latest'}: {e}")
        return None
