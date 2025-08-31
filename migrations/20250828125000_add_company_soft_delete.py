import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Add deleted_at column to companies table for soft deletion support"""
    # Add deleted_at column to companies table
    conn.execute(
        """
        ALTER TABLE companies
        ADD COLUMN deleted_at TEXT DEFAULT NULL
        """
    )

    # Create index on deleted_at for efficient filtering
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_companies_deleted_at
        ON companies(deleted_at)
        """
    )

    print(f"{datetime.now()} - Added deleted_at column and index to companies table")


def rollback(conn: sqlite3.Connection):
    """Remove deleted_at column and index from companies table"""
    try:
        # Drop the index first
        conn.execute("DROP INDEX IF EXISTS idx_companies_deleted_at")

        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # First, rename the current table
        conn.execute("ALTER TABLE companies RENAME TO companies_backup")

        # Recreate the original table without deleted_at
        conn.execute(
            """
            CREATE TABLE companies (
                company_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                details TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT '{}',
                activity_at TEXT DEFAULT NULL,
                last_activity TEXT DEFAULT NULL,
                reply_message TEXT
            )
            """
        )

        # Copy data back (excluding deleted_at column)
        conn.execute(
            """
            INSERT INTO companies (
                company_id, name, updated_at, details, status,
                activity_at, last_activity, reply_message
            )
            SELECT
                company_id, name, updated_at, details, status,
                activity_at, last_activity, reply_message
            FROM companies_backup
            """
        )

        # Drop the backup table
        conn.execute("DROP TABLE companies_backup")

        print(
            f"{datetime.now()} - Removed deleted_at column and index from companies table"
        )
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
