import logging
import os
import uuid
from typing import List, Dict, Any

import pandas as pd

from kodak.shared.utils import clean_num, load_config

logger = logging.getLogger(__name__)

config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

# DNB ASK account number
DNB_ACCOUNT_ID = '9017671'

# Column mapping (Norwegian -> English)
# Ticker, Navn, Handelsdato, Handelsretning, Antall, Pris, Totalbeløp, MIC, Valuta,
# Valutakurs, Transaksjons ID, Oppgjørsdato, Totalbeløp (lokal valuta), Transaksjonsgebyr

def parse(file_path: str) -> List[Dict[str, Any]]:
    """Parse DNB ASK Excel export."""
    try:
        # Skip first 5 rows (metadata), row 5 is header
        df = pd.read_excel(file_path, skiprows=5)
    except Exception as e:
        logger.error(f'Error reading DNB file {file_path}: {e}')
        return []

    if df.empty:
        logger.warning(f'No data found in {file_path}')
        return []

    results = []
    pre_split_shares = 0  # Track pre-split shares for BYTTE generation
    split_date = '2025-06-19'  # AENA 10:1 split date

    for _, row in df.iterrows():
        ticker = str(row.iloc[0]).strip()  # Ticker column

        # Skip empty rows
        if pd.isna(row.iloc[0]) or ticker == 'nan':
            continue

        trade_date = str(row.iloc[2])[:10]  # Handelsdato (trade date)
        direction = str(row.iloc[3]).upper()  # Handelsretning (Kjøpt = Buy)
        quantity = clean_num(row.iloc[4])  # Antall
        price = clean_num(row.iloc[5])  # Pris
        currency = str(row.iloc[8]).strip()  # Valuta
        exchange_rate = clean_num(row.iloc[9])  # Valutakurs
        fee_nok = clean_num(row.iloc[13])  # Transaksjonsgebyr (in NOK)

        # Map direction to type
        if 'KJØP' in direction or 'KJØ' in direction:
            txn_type = 'BUY'
        elif 'SALG' in direction or 'SOLGT' in direction:
            txn_type = 'SELL'
        else:
            txn_type = 'OTHER'
            logger.warning(f'Unknown direction: {direction}')

        # Normalize ticker - both AENA and AENA_OLD map to AENA.MC
        symbol = 'AENA.MC' if 'AENA' in ticker.upper() else ticker
        isin = 'ES0105046017' if symbol == 'AENA.MC' else None

        # Track pre-split shares
        is_pre_split = 'OLD' in ticker.upper() or (trade_date < split_date and 'AENA' in ticker.upper())
        if is_pre_split and txn_type == 'BUY':
            pre_split_shares += quantity

        # Calculate amounts
        amount = quantity * price  # In trading currency
        amount_local = amount * exchange_rate  # In NOK

        # Add DEPOSIT transaction (day before buy) - always positive
        deposit_date = pd.to_datetime(trade_date) - pd.Timedelta(days=1)
        deposit_amount = abs(amount_local) + fee_nok  # Total including fees

        # Sign convention: BUY = cash outflow (negative), SELL = cash inflow (positive)
        if txn_type == 'BUY':
            amount = -abs(amount)
            amount_local = -abs(amount_local)

        deposit = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': DNB_ACCOUNT_ID,
            'isin': None,
            'symbol': None,
            'date': deposit_date.strftime('%Y-%m-%d'),
            'type': 'DEPOSIT',
            'quantity': 0,
            'price': 0,
            'amount': deposit_amount,
            'currency': BASE_CURRENCY,
            'amount_local': deposit_amount,
            'exchange_rate': 1.0,
            'description': f'Deposit for {symbol} purchase',
            'source_file': os.path.basename(file_path),
            'fee': 0,
            'fee_currency': BASE_CURRENCY,
            'fee_local': 0
        }
        results.append(deposit)

        # Add BUY transaction
        buy = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': DNB_ACCOUNT_ID,
            'isin': isin,
            'symbol': symbol,
            'date': trade_date,
            'type': txn_type,
            'quantity': quantity if txn_type == 'BUY' else -quantity,
            'price': price,
            'amount': amount,
            'currency': currency,
            'amount_local': amount_local,
            'exchange_rate': exchange_rate,
            'description': f'{ticker} {"pre-split" if is_pre_split else "post-split"} purchase',
            'source_file': os.path.basename(file_path),
            'fee': fee_nok,
            'fee_currency': BASE_CURRENCY,
            'fee_local': fee_nok
        }
        results.append(buy)

    # Generate BYTTE (split) transactions if we have pre-split shares
    if pre_split_shares > 0:
        post_split_shares = pre_split_shares * 10  # 10:1 split

        # BYTTE UTTAK VP - shares out
        bytte_out = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': DNB_ACCOUNT_ID,
            'isin': 'ES0105046017',
            'symbol': 'AENA.MC',
            'date': split_date,
            'type': 'BYTTE UTTAK VP',
            'quantity': -pre_split_shares,
            'price': 0,
            'amount': 0,
            'currency': 'EUR',
            'amount_local': 0,
            'exchange_rate': 1.0,
            'description': f'AENA 10:1 stock split - {pre_split_shares} shares out',
            'source_file': os.path.basename(file_path),
            'fee': 0,
            'fee_currency': BASE_CURRENCY,
            'fee_local': 0
        }
        results.append(bytte_out)

        # BYTTE INNLEGG VP - shares in
        bytte_in = {
            'external_id': str(uuid.uuid4()),
            'account_external_id': DNB_ACCOUNT_ID,
            'isin': 'ES0105046017',
            'symbol': 'AENA.MC',
            'date': split_date,
            'type': 'BYTTE INNLEGG VP',
            'quantity': post_split_shares,
            'price': 0,
            'amount': 0,
            'currency': 'EUR',
            'amount_local': 0,
            'exchange_rate': 1.0,
            'description': f'AENA 10:1 stock split - {post_split_shares} shares in',
            'source_file': os.path.basename(file_path),
            'fee': 0,
            'fee_currency': BASE_CURRENCY,
            'fee_local': 0
        }
        results.append(bytte_in)

        logger.info(f'Generated BYTTE transactions for AENA split: {pre_split_shares} -> {post_split_shares}')

    logger.info(f'Parsed {len(results)} transactions from DNB file')
    return results
