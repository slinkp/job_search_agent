from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _activity_indicates_archived(activity_label: str | None) -> bool:
    """Detect historical archived labels, including misspelled variants."""
    if not activity_label:
        return False
    normalized = activity_label.strip().lower()
    return "archiv" in normalized or "archv" in normalized


def migrate(conn: sqlite3.Connection, dry_run: bool = False):
    """Backfill missing company.status.archived_at from legacy activity rows.

    This migration addresses legacy inconsistent data where a company's latest activity
    indicates archived state, but status.archived_at is missing.
    """

    columns = {row[1] for row in conn.execute("PRAGMA table_info(companies)")}
    if "status" not in columns:
        print("companies.status column not found; skipping archive-status backfill")
        return

    rows = conn.execute(
        "SELECT company_id, name, status, activity_at, last_activity FROM companies"
    ).fetchall()

    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"{datetime.now()} - Starting archive-status backfill ({mode})")

    candidates = 0
    updated = 0
    would_update = 0
    total_rows = len(rows)

    for company_id, company_name, status_json, activity_at, last_activity in rows:
        try:
            status = json.loads(status_json) if status_json else {}
        except json.JSONDecodeError:
            status = {}

        if status.get("archived_at"):
            continue
        if not _activity_indicates_archived(last_activity):
            continue

        candidates += 1
        archived_ts = _parse_dt(activity_at)
        ts_source = "companies.activity_at"
        if archived_ts is None:
            # Fall back to latest archived recruiter message timestamp if available.
            message_row = conn.execute(
                """
                SELECT archived_at
                FROM recruiter_messages
                WHERE company_id = ?
                  AND archived_at IS NOT NULL
                  AND archived_at != ''
                ORDER BY archived_at DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()
            archived_ts = _parse_dt(message_row[0]) if message_row else None
            ts_source = "recruiter_messages.archived_at"

        if archived_ts is None:
            print(
                f"[BAD] {company_name!r} company_id={company_id} "
                f"last_activity={last_activity!r} "
                "missing parseable archived timestamp (activity_at/recruiter_messages.archived_at)"
            )
            continue

        status["archived_at"] = archived_ts.isoformat()

        # Normalize typo/legacy labels to a canonical value once archive status is fixed.
        normalized_activity = (
            "company archived"
            if _activity_indicates_archived(last_activity)
            else last_activity
        )
        change_line = (
            f"{company_name!r} company_id={company_id} "
            f"archived_at={status['archived_at']} "
            f"source={ts_source} "
            f"last_activity:{last_activity!r}->{normalized_activity!r}"
        )
        if dry_run:
            print(f"[DRY-RUN] {change_line}")
            would_update += 1
            continue

        else:
            conn.execute(
                "UPDATE companies SET status = ?, last_activity = ? WHERE company_id = ?",
                (json.dumps(status), normalized_activity, company_id),
            )
            print(f"[UPDATED] {change_line}")
            updated += 1

    if dry_run:
        print(
            f"{datetime.now()} - Dry run complete: {candidates} candidate rows out of {total_rows}, "
            f"{would_update} rows would be updated"
        )
    else:
        print(f"{datetime.now()} - Backfilled archived status for {updated} companies")


def rollback(conn: sqlite3.Connection):
    # Non-destructive rollback: no-op. We avoid removing archived_at values.
    print(f"{datetime.now()} - No rollback changes for archive-status backfill")
