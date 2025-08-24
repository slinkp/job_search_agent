import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Add unique and lookup indexes for company_aliases"""
    # Unique active alias per company
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_company_aliases_company_norm_active
        ON company_aliases(company_id, normalized_alias)
        WHERE is_active = 1
        """
    )
    # Lookup by normalized alias (active only for typical lookups)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_company_aliases_normalized_alias
        ON company_aliases(normalized_alias)
        WHERE is_active = 1
        """
    )
    print(f"{datetime.now()} - Created indexes for company_aliases")


def rollback(conn: sqlite3.Connection):
    try:
        conn.execute("DROP INDEX IF EXISTS idx_company_aliases_company_norm_active")
        conn.execute("DROP INDEX IF EXISTS idx_company_aliases_normalized_alias")
        print(f"{datetime.now()} - Dropped indexes for company_aliases")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
