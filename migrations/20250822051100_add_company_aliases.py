import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Create company_aliases table"""
    # Create table if it doesn't exist
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS company_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            alias TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'auto',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies (company_id)
        )
        """
    )
    print(f"{datetime.now()} - Ensured company_aliases table exists")


def rollback(conn: sqlite3.Connection):
    """Drop company_aliases table"""
    try:
        conn.execute("DROP TABLE IF EXISTS company_aliases")
        print(f"{datetime.now()} - Dropped company_aliases table")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
