import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Backfill recruiter_messages.reply_sent_at from company.status.reply_sent_at"""

    # Get all messages where reply_sent_at is not set
    cursor = conn.execute(
        """
        SELECT message_id, company_id
        FROM recruiter_messages
        WHERE reply_sent_at IS NULL
    """
    )
    messages_to_update = cursor.fetchall()

    print(
        f"{datetime.now()} - Found {len(messages_to_update)} messages with NULL reply_sent_at"
    )

    updated_count = 0
    not_updated_count = 0

    for message_id, company_id in messages_to_update:
        # Get the company's status.reply_sent_at
        cursor = conn.execute(
            """
            SELECT status
            FROM companies
            WHERE company_id = ?
        """,
            (company_id,),
        )
        result = cursor.fetchone()

        if result and result[0]:
            import json

            try:
                status_data = json.loads(result[0])
                company_reply_sent_at = status_data.get("reply_sent_at")

                if company_reply_sent_at:
                    # Update the message's reply_sent_at
                    conn.execute(
                        """
                        UPDATE recruiter_messages
                        SET reply_sent_at = ?
                        WHERE message_id = ?
                    """,
                        (company_reply_sent_at, message_id),
                    )

                    updated_count += 1
                    print(
                        f"{datetime.now()} - Updated message {message_id} with reply_sent_at {company_reply_sent_at}"
                    )
                else:
                    not_updated_count += 1
            except json.JSONDecodeError:
                print(
                    f"{datetime.now()} - Warning: Invalid JSON in status for company {company_id}"
                )
                not_updated_count += 1
        else:
            not_updated_count += 1

    print(f"{datetime.now()} - Migration complete:")
    print(f"  - Updated: {updated_count} messages")
    print(f"  - Not updated: {not_updated_count} messages")


def rollback(conn: sqlite3.Connection):
    """Remove reply_sent_at values that were set by this migration"""
    # This is a backfill migration, so rollback would clear all reply_sent_at values
    # which might be too destructive. Instead, we'll just log a warning.
    print(f"{datetime.now()} - Warning: Rollback would clear all reply_sent_at values")
    print("This could affect legitimate data. Manual intervention required if needed.")
