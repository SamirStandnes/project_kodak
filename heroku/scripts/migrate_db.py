#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

Migrates data from local SQLite database to Heroku PostgreSQL.
Run this locally with your Heroku DATABASE_URL.

Usage:
    python -m heroku.scripts.migrate_db --sqlite database/portfolio.db --pg-url $DATABASE_URL

Or with environment variable:
    export DATABASE_URL=postgresql://...
    python -m heroku.scripts.migrate_db --sqlite database/portfolio.db
"""
import argparse
import logging
import os
import sqlite3
import sys

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_postgresql_schema(pg_conn, base_currency='NOK'):
    """Creates the PostgreSQL schema matching the SQLite schema."""
    cursor = pg_conn.cursor()

    # Drop existing tables (careful - this is destructive!)
    logger.info("Dropping existing tables if they exist...")
    cursor.execute("DROP TABLE IF EXISTS exchange_rates CASCADE")
    cursor.execute("DROP TABLE IF EXISTS market_prices CASCADE")
    cursor.execute("DROP TABLE IF EXISTS transactions CASCADE")
    cursor.execute("DROP TABLE IF EXISTS instruments CASCADE")
    cursor.execute("DROP TABLE IF EXISTS accounts CASCADE")

    # Create accounts table
    logger.info("Creating accounts table...")
    cursor.execute(f'''
        CREATE TABLE accounts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            broker TEXT,
            currency TEXT NOT NULL DEFAULT '{base_currency}',
            type TEXT,
            external_id TEXT UNIQUE
        )
    ''')

    # Create instruments table
    logger.info("Creating instruments table...")
    cursor.execute('''
        CREATE TABLE instruments (
            id SERIAL PRIMARY KEY,
            isin TEXT UNIQUE,
            symbol TEXT,
            name TEXT,
            type TEXT,
            currency TEXT,
            exchange_mic TEXT,
            sector TEXT,
            region TEXT,
            country TEXT,
            asset_class TEXT
        )
    ''')

    # Create transactions table
    logger.info("Creating transactions table...")
    cursor.execute('''
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            external_id TEXT UNIQUE,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            instrument_id INTEGER REFERENCES instruments(id),
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL,
            price REAL,
            amount REAL,
            currency TEXT NOT NULL,
            exchange_rate REAL,
            amount_local REAL,
            fee REAL,
            fee_currency TEXT,
            fee_local REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            batch_id TEXT,
            source_file TEXT,
            hash TEXT
        )
    ''')

    # Create market_prices table
    logger.info("Creating market_prices table...")
    cursor.execute('''
        CREATE TABLE market_prices (
            instrument_id INTEGER NOT NULL REFERENCES instruments(id),
            date TEXT NOT NULL,
            close REAL,
            currency TEXT,
            source TEXT,
            PRIMARY KEY (instrument_id, date)
        )
    ''')

    # Create exchange_rates table
    logger.info("Creating exchange_rates table...")
    cursor.execute('''
        CREATE TABLE exchange_rates (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            rate REAL,
            PRIMARY KEY (from_currency, to_currency, date)
        )
    ''')

    pg_conn.commit()
    logger.info("Schema created successfully")


def migrate_table(sqlite_conn, pg_conn, table_name, columns, has_serial_id=False):
    """Migrates a single table from SQLite to PostgreSQL."""
    logger.info(f"Migrating {table_name}...")

    # For tables with SERIAL id, we need to:
    # 1. Insert with explicit IDs
    # 2. Reset the sequence after

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    if has_serial_id:
        # Include id in the migration to preserve foreign key relationships
        all_columns = ['id'] + columns
    else:
        all_columns = columns

    # Fetch all rows from SQLite
    sqlite_cursor.execute(f"SELECT {','.join(all_columns)} FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    if not rows:
        logger.info(f"  No rows to migrate in {table_name}")
        return 0

    # Build INSERT statement
    placeholders = ','.join(['%s'] * len(all_columns))
    insert_sql = f"INSERT INTO {table_name} ({','.join(all_columns)}) VALUES ({placeholders})"

    # Insert rows
    inserted = 0
    for row in rows:
        try:
            pg_cursor.execute(insert_sql, row)
            inserted += 1
        except psycopg2.Error as e:
            logger.warning(f"  Error inserting row: {e}")

    # Reset sequence for tables with SERIAL
    if has_serial_id:
        pg_cursor.execute(f"""
            SELECT setval(pg_get_serial_sequence('{table_name}', 'id'),
                         COALESCE((SELECT MAX(id) FROM {table_name}), 1))
        """)

    pg_conn.commit()
    logger.info(f"  Migrated {inserted} rows")
    return inserted


def migrate(sqlite_path: str, pg_url: str, base_currency: str = 'NOK'):
    """Main migration function."""
    logger.info(f"Starting migration from {sqlite_path}")

    # Connect to SQLite
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found: {sqlite_path}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to PostgreSQL
    # Heroku provides postgres:// but psycopg2 needs postgresql://
    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    try:
        pg_conn = psycopg2.connect(pg_url)
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    # Create schema
    create_postgresql_schema(pg_conn, base_currency)

    # Define table migrations (order matters for foreign keys)
    tables = [
        ('accounts', ['name', 'broker', 'currency', 'type', 'external_id'], True),
        ('instruments', ['isin', 'symbol', 'name', 'type', 'currency', 'exchange_mic', 'sector', 'region', 'country', 'asset_class'], True),
        ('transactions', ['external_id', 'account_id', 'instrument_id', 'date', 'type', 'quantity', 'price', 'amount', 'currency', 'exchange_rate', 'amount_local', 'fee', 'fee_currency', 'fee_local', 'created_at', 'notes', 'batch_id', 'source_file', 'hash'], True),
        ('market_prices', ['instrument_id', 'date', 'close', 'currency', 'source'], False),
        ('exchange_rates', ['from_currency', 'to_currency', 'date', 'rate'], False),
    ]

    total_rows = 0
    for table_name, columns, has_serial_id in tables:
        try:
            rows = migrate_table(sqlite_conn, pg_conn, table_name, columns, has_serial_id)
            total_rows += rows
        except Exception as e:
            logger.error(f"Failed to migrate {table_name}: {e}")

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    logger.info(f"Migration complete! Total rows migrated: {total_rows}")


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite database to PostgreSQL')
    parser.add_argument('--sqlite', required=True, help='Path to SQLite database file')
    parser.add_argument('--pg-url', help='PostgreSQL connection URL (or use DATABASE_URL env var)')
    parser.add_argument('--base-currency', default='NOK', help='Base currency (default: NOK)')

    args = parser.parse_args()

    # Get PostgreSQL URL
    pg_url = args.pg_url or os.environ.get('DATABASE_URL')
    if not pg_url:
        logger.error("PostgreSQL URL not provided. Use --pg-url or set DATABASE_URL environment variable")
        sys.exit(1)

    migrate(args.sqlite, pg_url, args.base_currency)


if __name__ == '__main__':
    main()
