import hashlib
import logging
import os
import pandas as pd
from typing import Optional, Union

def setup_logging(script_name: str) -> str:
    """Configures logging to file and console."""
    log_dir = os.path.join('data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{script_name}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def clean_num(val: Union[str, float, int, None]) -> float:
    """Converts various number formats to float safely."""
    if pd.isna(val) or val == '':
        return 0.0
    if isinstance(val, (float, int)):
        return float(val)
    val = str(val).replace(' ', '').replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0.0

def generate_txn_hash(date: str, account_id: str, type: str, symbol: str, amount: float) -> str:
    """Generates a stable hash to identify duplicate transactions."""
    # Ensure consistent string formatting
    date_str = str(date).split(' ')[0] # YYYY-MM-DD
    amt_str = f"{amount:.2f}"
    
    raw_str = f"{date_str}|{account_id}|{type}|{symbol}|{amt_str}"
    return hashlib.md5(raw_str.encode()).hexdigest()
