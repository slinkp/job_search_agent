import json
import sqlite3
from datetime import datetime, timezone


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Handle both naive and offset-aware ISO strings
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _max_candidate(
    current: tuple[datetime | None, str | None], candidate_dt: datetime | None, label: str
):
    current_dt, _ = current
    if candidate_dt and (current_dt is None or candidate_dt > current_dt):
        return candidate_dt, label
    return current


def migrate(conn: sqlite3.Connection):
    """Backfill companies.activity_at and companies.last_activity from existing data.

    Sources considered (in priority by latest timestamp):
      - recruiter_messages.reply_sent_at -> "reply sent"
      - company.status.reply_sent_at -> "reply sent"
      - recruiter_messages.archived_at -> "message archived"
      - company.status.archived_at -> "company archived"
      - recruiter_messages.date -> "message received"
      - events table (REPLY_SENT, ARCHIVED) if present

    Excludes research completion/import events per Issue #16.
    """

    # Ensure columns exist; if not, do nothing
    cols = {row[1] for row in conn.execute("PRAGMA table_info(companies)")}
    if "activity_at" not in cols or "last_activity" not in cols:
        print(
            "activity_at/last_activity columns not found on companies; skipping backfill"
        )
        return

    # Check whether events table exists
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    has_events = "events" in tables

    company_rows = conn.execute(
        "SELECT company_id, status, reply_message FROM companies WHERE activity_at IS NULL OR last_activity IS NULL"
    ).fetchall()

    updated = 0
    for company_id, status_json, reply_message in company_rows:
        latest: tuple[datetime | None, str | None] = (None, None)

        # From recruiter_messages
        # reply sent
        for row in conn.execute(
            "SELECT reply_sent_at FROM recruiter_messages WHERE company_id = ? AND reply_sent_at IS NOT NULL AND reply_sent_at != ''",
            (company_id,),
        ):
            latest = _max_candidate(latest, _parse_dt(row[0]), "reply sent")

        # message archived
        for row in conn.execute(
            "SELECT archived_at FROM recruiter_messages WHERE company_id = ? AND archived_at IS NOT NULL AND archived_at != ''",
            (company_id,),
        ):
            latest = _max_candidate(latest, _parse_dt(row[0]), "message archived")

        # message received
        for row in conn.execute(
            "SELECT date FROM recruiter_messages WHERE company_id = ? AND date IS NOT NULL AND date != ''",
            (company_id,),
        ):
            latest = _max_candidate(latest, _parse_dt(row[0]), "message received")

        # From status JSON
        try:
            status = json.loads(status_json) if status_json else {}
        except json.JSONDecodeError:
            status = {}

        latest = _max_candidate(
            latest, _parse_dt(status.get("reply_sent_at")), "reply sent"
        )
        latest = _max_candidate(
            latest, _parse_dt(status.get("archived_at")), "company archived"
        )

        # From events if present
        if has_events:
            for row in conn.execute(
                "SELECT event_type, timestamp FROM events WHERE company_id = ? AND event_type IN ('reply_sent','archived')",
                (company_id,),
            ):
                event_type, ts = row
                label = "reply sent" if event_type == "reply_sent" else "company archived"
                latest = _max_candidate(latest, _parse_dt(ts), label)

        # If we still have nothing but a reply draft exists, use updated_at as best-effort
        if latest[0] is None and reply_message:
            row = conn.execute(
                "SELECT updated_at FROM companies WHERE company_id = ?",
                (company_id,),
            ).fetchone()
            latest = _max_candidate(
                latest, _parse_dt(row[0] if row else None), "reply generated"
            )

        if latest[0] is not None and latest[1] is not None:
            conn.execute(
                "UPDATE companies SET activity_at = ?, last_activity = ? WHERE company_id = ?",
                (latest[0].isoformat(), latest[1], company_id),
            )
            updated += 1

    print(f"{datetime.now()} - Backfilled activity fields for {updated} companies")


def rollback(conn: sqlite3.Connection):
    # Non-destructive rollback: clear the backfilled fields
    try:
        conn.execute("UPDATE companies SET activity_at = NULL, last_activity = NULL")
        print(
            f"{datetime.now()} - Cleared activity_at and last_activity for all companies"
        )
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
