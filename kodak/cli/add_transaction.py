"""CLI tool for adding manual transactions."""
import sys
from datetime import datetime

from kodak.shared.db import get_db_connection
from kodak.shared.utils import load_config, generate_txn_hash
from kodak.shared.parser_utils import VALID_TRANSACTION_TYPES

config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

# Common transaction types for display
COMMON_TYPES = ['BUY', 'SELL', 'DIVIDEND', 'DEPOSIT', 'WITHDRAWAL', 'INTEREST', 'FEE', 'TRANSFER_IN', 'TRANSFER_OUT']

COMMON_CURRENCIES = ['USD', 'EUR', 'GBP', 'NOK', 'SEK', 'DKK', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SGD']


def prompt(label: str, default: str = None, required: bool = True) -> str:
    """Prompt for input with optional default."""
    if default:
        user_input = input(f"{label} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        while True:
            user_input = input(f"{label}: ").strip()
            if user_input or not required:
                return user_input
            print("  This field is required.")


def prompt_float(label: str, default: float = 0.0) -> float:
    """Prompt for a float value."""
    while True:
        user_input = input(f"{label} [{default}]: ").strip()
        if not user_input:
            return default
        try:
            return float(user_input.replace(',', '.').replace(' ', ''))
        except ValueError:
            print("  Please enter a valid number.")


def prompt_date(label: str) -> str:
    """Prompt for a date in YYYY-MM-DD format."""
    today = datetime.now().strftime('%Y-%m-%d')
    while True:
        user_input = input(f"{label} [{today}]: ").strip()
        if not user_input:
            return today
        try:
            datetime.strptime(user_input, '%Y-%m-%d')
            return user_input
        except ValueError:
            print("  Please enter date as YYYY-MM-DD.")


def prompt_currency() -> str:
    """Prompt for currency with common options."""
    print("\nAsset currency:")
    for i, c in enumerate(COMMON_CURRENCIES, 1):
        print(f"  {i:2}. {c}", end="")
        if (i) % 4 == 0:
            print()
    print(f"\n  Or type a custom 3-letter code")

    while True:
        user_input = input(f"Currency [1=USD]: ").strip()
        if not user_input:
            return 'USD'
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(COMMON_CURRENCIES):
                return COMMON_CURRENCIES[idx]
        elif len(user_input) == 3 and user_input.isalpha():
            return user_input.upper()
        print("  Please select 1-12 or enter a 3-letter currency code.")


def prompt_type() -> str:
    """Prompt for transaction type with options."""
    print("\nTransaction types:")
    for i, t in enumerate(COMMON_TYPES, 1):
        print(f"  {i}. {t}")
    print(f"  Or type a custom value")

    while True:
        user_input = input("Type [1-9 or custom]: ").strip()
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(COMMON_TYPES):
                return COMMON_TYPES[idx]
        elif user_input.upper() in VALID_TRANSACTION_TYPES:
            return user_input.upper()
        elif user_input:
            confirm = input(f"  Use custom type '{user_input.upper()}'? (y/n): ").strip().lower()
            if confirm == 'y':
                return user_input.upper()
        print("  Please select a valid option.")


def get_or_create_account(cursor, account_name: str) -> int:
    """Get account ID, creating if it doesn't exist."""
    cursor.execute("SELECT id FROM accounts WHERE name = ?", (account_name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Create new account
    cursor.execute(
        "INSERT INTO accounts (name, currency, external_id) VALUES (?, ?, ?)",
        (account_name, BASE_CURRENCY, account_name)
    )
    return cursor.lastrowid


def get_or_create_instrument(cursor, symbol: str, isin: str, currency: str) -> int:
    """Get instrument ID, creating if it doesn't exist."""
    if isin:
        cursor.execute("SELECT id FROM instruments WHERE isin = ?", (isin,))
        row = cursor.fetchone()
        if row:
            return row[0]

    if symbol:
        cursor.execute("SELECT id FROM instruments WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Create new instrument
    cursor.execute(
        "INSERT INTO instruments (isin, symbol, currency) VALUES (?, ?, ?)",
        (isin or None, symbol, currency)
    )
    return cursor.lastrowid


def add_transaction():
    """Interactive CLI to add a manual transaction."""
    print(f"\n{'='*50}")
    print(f"  Add Manual Transaction ({BASE_CURRENCY})")
    print(f"{'='*50}\n")

    # Collect inputs
    date = prompt_date("Date (YYYY-MM-DD)")
    txn_type = prompt_type()
    account = prompt("Account name", required=True)

    # Instrument (optional for deposits/withdrawals)
    needs_instrument = txn_type in ['BUY', 'SELL', 'DIVIDEND', 'TRANSFER_IN', 'TRANSFER_OUT']
    symbol = None
    isin = None
    instrument_currency = BASE_CURRENCY

    if needs_instrument:
        symbol = prompt("Symbol (e.g., AAPL, BTC-USD)", required=True)
        isin = prompt("ISIN (optional, press Enter to skip)", required=False)
        instrument_currency = prompt_currency()

    quantity = prompt_float("Quantity", default=0.0)
    price = prompt_float("Price per unit", default=0.0)

    # Calculate amount if not provided
    default_amount = round(quantity * price, 2) if quantity and price else 0.0
    if txn_type in ['BUY', 'TRANSFER_IN']:
        default_amount = -abs(default_amount)  # Outflow
    elif txn_type in ['SELL', 'DIVIDEND']:
        default_amount = abs(default_amount)  # Inflow

    amount = prompt_float(f"Amount in {instrument_currency}", default=default_amount)

    # FX handling
    if instrument_currency != BASE_CURRENCY:
        exchange_rate = prompt_float(f"Exchange rate ({instrument_currency} -> {BASE_CURRENCY})", default=1.0)
        amount_local = round(amount * exchange_rate, 2)
        print(f"  -> Amount in {BASE_CURRENCY}: {amount_local}")
    else:
        exchange_rate = 1.0
        amount_local = amount

    fee = prompt_float("Fee (in asset currency)", default=0.0)
    fee_local = round(fee * exchange_rate, 2) if fee else 0.0

    description = prompt("Description/Notes (optional)", required=False)

    # Summary
    print(f"\n{'='*50}")
    print("  Transaction Summary")
    print(f"{'='*50}")
    print(f"  Date:        {date}")
    print(f"  Type:        {txn_type}")
    print(f"  Account:     {account}")
    if symbol:
        print(f"  Symbol:      {symbol}")
    if isin:
        print(f"  ISIN:        {isin}")
    print(f"  Quantity:    {quantity}")
    print(f"  Price:       {price}")
    print(f"  Amount:      {amount} {instrument_currency}")
    if instrument_currency != BASE_CURRENCY:
        print(f"  FX Rate:     {exchange_rate}")
        print(f"  Amount Local:{amount_local} {BASE_CURRENCY}")
    if fee:
        print(f"  Fee:         {fee_local} {BASE_CURRENCY}")
    if description:
        print(f"  Notes:       {description}")
    print(f"{'='*50}\n")

    confirm = input("Save this transaction? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    # Save to database
    with get_db_connection() as conn:
        cursor = conn.cursor()

        account_id = get_or_create_account(cursor, account)

        instrument_id = None
        if symbol or isin:
            instrument_id = get_or_create_instrument(cursor, symbol, isin, instrument_currency)

        # Generate hash for deduplication
        txn_hash = generate_txn_hash(date, account, txn_type, symbol or '', amount)

        # Check for duplicate
        cursor.execute("SELECT id FROM transactions WHERE hash = ?", (txn_hash,))
        if cursor.fetchone():
            print("\n[WARNING] A similar transaction already exists. Skipping.")
            return

        import uuid
        external_id = str(uuid.uuid4())

        cursor.execute('''
            INSERT INTO transactions (
                external_id, account_id, instrument_id, date, type,
                quantity, price, amount, currency,
                amount_local, exchange_rate, fee, fee_currency, fee_local,
                notes, source_file, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            external_id, account_id, instrument_id, date, txn_type,
            quantity, price, amount, instrument_currency,
            amount_local, exchange_rate, fee, instrument_currency, fee_local,
            description, 'manual_entry', txn_hash
        ))

        conn.commit()
        print(f"\n[SUCCESS] Transaction added! (ID: {cursor.lastrowid})")


if __name__ == '__main__':
    try:
        add_transaction()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
