#!/usr/bin/env python3
"""
Migration script to move research errors from details to status
and add status field to companies table.
"""
import datetime
import json
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate_database(db_path="data/companies.db"):
    """Migrate the database to use the new status field."""

    # Create a backup of the database before migration

    # Generate a backup filename with timestamp
    backup_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{backup_timestamp}"

    # Create the backup
    try:
        shutil.copy2(db_path, backup_path)
        print(f"Database backup created at: {backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check if status column exists and get column info
    cursor = conn.execute("PRAGMA table_info(companies)")
    columns_info = {row["name"]: row for row in cursor.fetchall()}

    # Begin a transaction for all changes
    conn.execute("BEGIN TRANSACTION")

    try:
        # Add status column if it doesn't exist
        if "status" not in columns_info:
            print("Adding status column to companies table...")
            conn.execute("ALTER TABLE companies ADD COLUMN status TEXT DEFAULT '{}'")
        else:
            # SQLite doesn't directly support ALTER COLUMN SET DEFAULT
            # We need to ensure existing NULL values are set to '{}'
            print("Ensuring status column has correct values...")
            conn.execute(
                "UPDATE companies SET status = '{}' WHERE status IS NULL OR status = ''"
            )

        # Handle details column - ensure it exists with proper default
        if "details" not in columns_info:
            print("Adding details column to companies table...")
            conn.execute("ALTER TABLE companies ADD COLUMN details TEXT DEFAULT '{}'")
        else:
            # Set empty details to '{}'
            print("Ensuring details column has correct values...")
            conn.execute(
                "UPDATE companies SET details = '{}' WHERE details IS NULL OR details = ''"
            )

        # In SQLite, to change a column default, we need to:
        # 1. Create a new table with the desired schema
        # 2. Copy data from old table to new table
        # 3. Drop old table
        # 4. Rename new table to original name

        print("Updating column defaults...")
        conn.execute(
            """
            CREATE TABLE companies_new (
                name TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                details TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT '{}',
                reply_message TEXT,
                message_id TEXT
            )
        """
        )

        conn.execute(
            """
            INSERT INTO companies_new (name, updated_at, details, status, reply_message, message_id)
            SELECT name, updated_at, details, status, reply_message, message_id FROM companies
        """
        )

        conn.execute("DROP TABLE companies")
        conn.execute("ALTER TABLE companies_new RENAME TO companies")

        # Now migrate all companies to move research_errors from details to status
        print("Migrating research errors from details to status...")
        cursor = conn.execute("SELECT name, details, status FROM companies")
        companies = cursor.fetchall()

        for company in companies:
            name = company["name"]
            details_str = company["details"]
            status_str = company["status"]

            try:
                details = json.loads(details_str) if details_str else {}
            except json.JSONDecodeError:
                print(f"Invalid JSON in details for {name}, resetting to {{}}")
                details = {}

            try:
                status = json.loads(status_str) if status_str else {}
            except json.JSONDecodeError:
                print(f"Invalid JSON in status for {name}, resetting to {{}}")
                status = {}

            # Move research_errors if they exist in details
            if "research_errors" in details:
                print(f"Moving research_errors for {name}...")
                status["research_errors"] = details.pop("research_errors")

            # Check for archived status from events
            cursor = conn.execute(
                "SELECT timestamp FROM events WHERE company_name = ? AND event_type = 'archived' ORDER BY timestamp DESC LIMIT 1",
                (name,),
            )
            archived_event = cursor.fetchone()
            if archived_event:
                print(f"Setting archived_at for {name}...")
                status["archived_at"] = archived_event["timestamp"]

            # Check for reply_sent events to set reply_sent_at
            cursor = conn.execute(
                "SELECT timestamp FROM events WHERE company_name = ? AND event_type = 'reply_sent' ORDER BY timestamp DESC LIMIT 1",
                (name,),
            )
            reply_event = cursor.fetchone()
            if reply_event:
                status["reply_sent_at"] = reply_event["timestamp"]

            # Update the company with the new status and details
            conn.execute(
                "UPDATE companies SET details = ?, status = ? WHERE name = ?",
                (json.dumps(details), json.dumps(status), name),
            )

        conn.commit()
        print(f"Migration complete. Updated {len(companies)} companies.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migrate_database()
