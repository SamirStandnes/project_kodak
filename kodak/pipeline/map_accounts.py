import logging
import os
import pandas as pd

from kodak.shared.db import get_db_connection

logger = logging.getLogger(__name__)

ACCOUNTS_MAP_PATH = os.path.join('data', 'reference', 'accounts_map.csv')

def map_accounts():
    if not os.path.exists(ACCOUNTS_MAP_PATH):
        logger.warning(f"Accounts map not found at {ACCOUNTS_MAP_PATH}")
        return

    logger.info("Loading Accounts map...")
    df_map = pd.read_csv(ACCOUNTS_MAP_PATH)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        updates = 0
        for _, row in df_map.iterrows():
            ext_id = str(row['external_id'])
            name = row['name']
            broker = row.get('broker')
            acc_type = row.get('type')

            # Update account
            cursor.execute("""
                UPDATE accounts
                SET name = ?, broker = ?, type = ?
                WHERE external_id = ?
            """, (name, broker, acc_type, ext_id))

            if cursor.rowcount > 0:
                updates += cursor.rowcount

        conn.commit()
    logger.info(f"Updated {updates} accounts based on accounts_map.csv.")

if __name__ == "__main__":
    map_accounts()
