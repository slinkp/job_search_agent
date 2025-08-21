import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Add activity_at and last_activity columns to companies table"""
    try:
        conn.execute("ALTER TABLE companies ADD COLUMN activity_at TEXT DEFAULT NULL")
        print(f"{datetime.now()} - Added activity_at column to companies")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("activity_at column already exists")
        else:
            raise

    try:
        conn.execute("ALTER TABLE companies ADD COLUMN last_activity TEXT DEFAULT NULL")
        print(f"{datetime.now()} - Added last_activity column to companies")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("last_activity column already exists")
        else:
            raise


def rollback(conn: sqlite3.Connection):
    """Rollback by recreating companies table without the new columns.

    Note: SQLite does not support DROP COLUMN directly. We recreate the table
    without the columns, copying existing data for the kept columns.
    """
    try:
        conn.execute(
            """
            CREATE TABLE companies_backup AS
            SELECT company_id, name, updated_at, details, status, reply_message
            FROM companies
            """
        )
        conn.execute("DROP TABLE companies")
        conn.execute(
            """
            ALTER TABLE companies_backup RENAME TO companies
            """
        )
        print(f"{datetime.now()} - Removed activity_at and last_activity columns from companies")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise


