"""
Migration to normalize compensation values stored in dollars to thousands.

This migration converts compensation values that are stored in full dollars
(e.g., 200000) to thousands (e.g., 200) to match the new storage convention.
Values over 1000 are assumed to be in dollars and are divided by 1000.
"""

import decimal
import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    import json

    # Get all companies directly from the connection
    cursor = conn.execute(
        "SELECT company_id, name, details FROM companies WHERE details IS NOT NULL"
    )
    companies = cursor.fetchall()

    updated_count = 0
    skipped_count = 0

    print(
        f"{datetime.now()} - Checking {len(companies)} companies for compensation normalization"
    )

    for company_id, name, details_json in companies:
        try:
            details = json.loads(details_json) if details_json else {}
        except json.JSONDecodeError:
            print(
                f"{datetime.now()} - Warning: Invalid JSON in details for company {company_id}"
            )
            skipped_count += 1
            continue

        if not details:
            skipped_count += 1
            continue

        needs_update = False
        updates = []

        # Helper function to check and normalize a compensation value
        def should_normalize(value):
            """Return True if value appears to be in dollars (>1000) and needs normalization."""
            if value is None:
                return False
            # Convert to float for comparison
            try:
                val = float(value)
                return val > 1000
            except (ValueError, TypeError):
                return False

        # Check and normalize total_comp
        if "total_comp" in details and details["total_comp"] is not None:
            if should_normalize(details["total_comp"]):
                old_value = details["total_comp"]
                details["total_comp"] = round(float(details["total_comp"]) / 1000)
                needs_update = True
                updates.append(f"total_comp: {old_value} -> {details['total_comp']}")

        # Check and normalize base
        if "base" in details and details["base"] is not None:
            if should_normalize(details["base"]):
                old_value = details["base"]
                details["base"] = round(float(details["base"]) / 1000)
                needs_update = True
                updates.append(f"base: {old_value} -> {details['base']}")

        # Check and normalize RSU
        if "rsu" in details and details["rsu"] is not None:
            if should_normalize(details["rsu"]):
                old_value = details["rsu"]
                details["rsu"] = round(float(details["rsu"]) / 1000)
                needs_update = True
                updates.append(f"rsu: {old_value} -> {details['rsu']}")

        # Check and normalize bonus
        if "bonus" in details and details["bonus"] is not None:
            if should_normalize(details["bonus"]):
                old_value = details["bonus"]
                details["bonus"] = round(float(details["bonus"]) / 1000)
                needs_update = True
                updates.append(f"bonus: {old_value} -> {details['bonus']}")

        # Update the database if any values were normalized
        if needs_update:
            try:
                conn.execute(
                    "UPDATE companies SET details = ? WHERE company_id = ?",
                    (json.dumps(details), company_id),
                )
                updated_count += 1
                print(
                    f"{datetime.now()} - Normalized {name} ({company_id}): {', '.join(updates)}"
                )
            except Exception as e:
                print(f"{datetime.now()} - Error updating company {company_id}: {e}")
        else:
            skipped_count += 1

    print(f"{datetime.now()} - Migration complete:")
    print(f"  - Normalized: {updated_count} companies")
    print(
        f"  - Skipped (already normalized or no compensation data): {skipped_count} companies"
    )


def rollback(conn: sqlite3.Connection):
    """
    Rollback would multiply values by 1000, but this risks data corruption
    since we can't distinguish between:
    - Values that were originally in thousands (should be left alone)
    - Values that were normalized by this migration (should be multiplied back)

    Manual intervention required if rollback is needed.
    """
    print(f"{datetime.now()} - Warning: Automated rollback not safe for this migration")
    print("This migration normalized compensation values from dollars to thousands.")
    print("Rollback would require manual intervention to restore original values,")
    print("as we cannot distinguish between originally-correct and migrated values.")
    print(
        "If you need to rollback, restore from a database backup taken before migration."
    )
