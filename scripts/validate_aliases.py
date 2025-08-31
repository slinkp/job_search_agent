#!/usr/bin/env python3
"""
Data validation script to check for orphaned aliases after company merges.

This script identifies aliases that point to companies that have been soft-deleted,
which would indicate incomplete cleanup after a company merge operation.
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List


def check_orphaned_aliases(db_path: str) -> List[Dict]:
    """
    Check for aliases that point to soft-deleted companies.

    Args:
        db_path: Path to the SQLite database

    Returns:
        List of orphaned alias records with company_id, alias, and source
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT ca.company_id, ca.alias, ca.source, ca.id
            FROM company_aliases ca
            LEFT JOIN companies c ON ca.company_id = c.company_id
            WHERE c.company_id IS NULL
            ORDER BY ca.company_id, ca.alias
        """
        )

        orphaned = []
        for row in cursor.fetchall():
            orphaned.append(
                {
                    "company_id": row[0],
                    "alias": row[1],
                    "source": row[2],
                    "alias_id": row[3],
                }
            )

    return orphaned


def main():
    parser = argparse.ArgumentParser(
        description="Check for orphaned aliases after company merges"
    )
    parser.add_argument("--db", default="data/companies.db", help="Path to database file")
    parser.add_argument("--fix", action="store_true", help="Remove orphaned aliases")

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    print(f"Checking for orphaned aliases in {db_path}...")

    orphaned = check_orphaned_aliases(str(db_path))

    if not orphaned:
        print("✓ No orphaned aliases found")
    else:
        print(f"⚠ Found {len(orphaned)} orphaned aliases:")
        for alias in orphaned:
            print(f"  - Company ID: {alias['company_id']}")
            print(f"    Alias: {alias['alias']}")
            print(f"    Source: {alias['source']}")
            print(f"    Alias ID: {alias['alias_id']}")
            print()

        if args.fix:
            print("Removing orphaned aliases...")
            with sqlite3.connect(str(db_path)) as conn:
                for alias in orphaned:
                    conn.execute(
                        "DELETE FROM company_aliases WHERE id = ?", (alias["alias_id"],)
                    )
                conn.commit()
            print(f"✓ Removed {len(orphaned)} orphaned aliases")
        else:
            print("Use --fix to remove orphaned aliases")

    # Return error code if any issues found
    if orphaned:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
