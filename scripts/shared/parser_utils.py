import uuid
import pandas as pd
from typing import Dict, Any
from scripts.shared.utils import clean_num as _clean_num, load_config

# --- Constants ---
config = load_config()
BASE_CURRENCY = config.get('base_currency', 'NOK')

# Standard Schema Contract
def create_empty_transaction() -> Dict[str, Any]:
    """Returns a dictionary with all required keys initialized to safe defaults."""
    return {
        'external_id': str(uuid.uuid4()),
        'account_external_id': None,
        'isin': None,
        'symbol': None,
        'date': None,
        'type': 'OTHER',
        'quantity': 0.0,
        'price': 0.0,
        'amount': 0.0,        # Asset Currency
        'currency': BASE_CURRENCY,
        'amount_local': 0.0,  # Base Currency
        'exchange_rate': 1.0,
        'description': '',
        'source_file': '',
        'fee': 0.0,
        'fee_currency': BASE_CURRENCY,
        'fee_local': 0.0
    }

def clean_num(val) -> float:
    """Wrapper for shared clean_num."""
    return _clean_num(val)

def apply_sign_logic(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically sets the sign of amount/amount_local based on transaction type.
    Example: BUY/WITHDRAWAL -> Negative. SELL/DEPOSIT -> Positive.
    """
    t_type = item.get('type', 'OTHER')
    
    outflow = ['BUY', 'WITHDRAWAL', 'TRANSFER_OUT', 'TAX', 'FEE']
    inflow = ['SELL', 'DEPOSIT', 'TRANSFER_IN', 'DIVIDEND', 'INTEREST']
    
    # Force absolute first to clean mixed input
    amt = abs(item['amount'])
    local = abs(item['amount_local'])
    qty = abs(item['quantity'])
    
    if t_type in outflow:
        item['amount'] = -amt
        item['amount_local'] = -local
        # Qty is positive for BUY (you gain shares), negative only for SELL/TRANSFER_OUT?
        # Actually in this system:
        # BUY: Qty +
        # SELL: Qty -
        # TRANSFER_OUT: Qty -
        if t_type in ['BUY']:
            item['quantity'] = qty
        else:
            item['quantity'] = -qty # Transfer out loses shares (if applicable)
            
    elif t_type in inflow:
        item['amount'] = amt
        item['amount_local'] = local
        if t_type in ['SELL', 'TRANSFER_OUT']: # Wait, SELL is outflow of shares
             item['quantity'] = -qty
        elif t_type in ['TRANSFER_IN', 'DEPOSIT', 'DIVIDEND']:
             item['quantity'] = qty # Gaining shares or cash
             if t_type == 'SELL': # Sell reduces qty
                 item['quantity'] = -qty

    # Refined Logic for Shares specifically
    if t_type == 'SELL':
        item['quantity'] = -abs(qty)
    elif t_type == 'BUY':
        item['quantity'] = abs(qty)
        
    return item
