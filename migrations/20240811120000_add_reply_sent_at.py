import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Add reply_sent_at column to recruiter_messages table"""
    try:
        conn.execute(
            "ALTER TABLE recruiter_messages ADD COLUMN reply_sent_at TEXT DEFAULT NULL"
        )
        print(f"{datetime.now()} - Added reply_sent_at column to recruiter_messages")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("reply_sent_at column already exists")
        else:
            raise


def rollback(conn: sqlite3.Connection):
    """Remove reply_sent_at column from recruiter_messages table"""
    try:
        conn.execute(
            "CREATE TABLE recruiter_messages_backup AS SELECT message_id, company_id, subject, sender, message, thread_id, email_thread_link, date, archived_at FROM recruiter_messages"
        )
        conn.execute("DROP TABLE recruiter_messages")
        conn.execute("ALTER TABLE recruiter_messages_backup RENAME TO recruiter_messages")
        print(f"{datetime.now()} - Removed reply_sent_at column from recruiter_messages")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
