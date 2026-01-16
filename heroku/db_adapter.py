"""
PostgreSQL database adapter for Heroku deployment.
Provides the same interface as kodak/shared/db.py but uses PostgreSQL.
"""
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Generator

# Import SQL translation
from heroku.sql_compat import translate_query

# --- Configuration ---
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Heroku provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


class DictRow(dict):
    """A dict subclass that also supports index-based access like sqlite3.Row."""
    def __init__(self, data: dict):
        super().__init__(data)
        self._keys = list(data.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self[self._keys[key]]
        return super().__getitem__(key)

    def keys(self):
        return self._keys


def get_connection():
    """Establishes a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

    conn = psycopg2.connect(DATABASE_URL)
    return conn


@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """Context manager for database connections. Ensures proper cleanup."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def create_backup(label: str = "manual") -> str:
    """
    Backup stub for PostgreSQL.
    On Heroku, backups are managed by Heroku Postgres addon.
    """
    logging.info(f"Backup requested with label '{label}' - use Heroku Postgres backups instead")
    return "heroku-managed"


def execute_query(query: str, params: tuple = ()) -> List[DictRow]:
    """Executes a read-only query and returns all results as dict-like rows."""
    conn = get_connection()
    try:
        # Translate SQLite syntax to PostgreSQL
        pg_query = translate_query(query)

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(pg_query, params)
        rows = cursor.fetchall()
        return [DictRow(dict(row)) for row in rows]
    finally:
        conn.close()


def execute_scalar(query: str, params: tuple = ()) -> Any:
    """Executes a query and returns the first column of the first row."""
    conn = get_connection()
    try:
        pg_query = translate_query(query)

        cursor = conn.cursor()
        cursor.execute(pg_query, params)
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def execute_non_query(query: str, params: tuple = ()) -> int:
    """Executes a write query (INSERT, UPDATE, DELETE) and returns row count."""
    conn = get_connection()
    try:
        pg_query = translate_query(query)

        cursor = conn.cursor()
        cursor.execute(pg_query, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def execute_batch(query: str, params_list: List[tuple]) -> int:
    """Executes a batch INSERT/UPDATE."""
    conn = get_connection()
    try:
        pg_query = translate_query(query)

        cursor = conn.cursor()
        cursor.executemany(pg_query, params_list)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logging.error(f"Database batch error: {e}")
        raise
    finally:
        conn.close()
