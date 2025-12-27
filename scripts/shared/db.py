import sqlite3
import os

def get_db_path():
    """Returns the absolute path to the portfolio database."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(project_root, 'database', 'portfolio.db')

def get_db_connection():
    """Returns a sqlite3 connection to the portfolio database."""
    db_path = get_db_path()
    return sqlite3.connect(db_path)
