import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional

# --- Configuration ---
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'database', 'portfolio.db')

def get_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database with Row factory enabled."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run setup/initialize_database.py first.")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def execute_query(query: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Executes a read-only query and returns all results."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()

def execute_scalar(query: str, params: tuple = ()) -> Any:
    """Executes a query and returns the first column of the first row."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def execute_non_query(query: str, params: tuple = ()) -> int:
    """Executes a write query (INSERT, UPDATE, DELETE) and returns row count."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
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
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logging.error(f"Database batch error: {e}")
        raise
    finally:
        conn.close()
