import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Seed each company's current name as a company_alias (source='seed')."""
    # Lazy import to avoid heavy module load if unused
    from models import normalize_company_name

    cursor = conn.execute(
        "SELECT company_id, name FROM companies WHERE name IS NOT NULL AND TRIM(name) != ''"
    )
    rows = cursor.fetchall()

    inserted = 0
    skipped = 0

    for company_id, name in rows:
        normalized = normalize_company_name(name)
        # Insert if not already present as an active alias
        try:
            conn.execute(
                """
                INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                VALUES (?, ?, ?, 'seed', 1)
                """,
                (company_id, name, normalized),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # Likely duplicate active alias due to unique index; skip
            skipped += 1

    print(
        f"{datetime.now()} - Seeded canonical aliases: inserted={inserted}, skipped={skipped}"
    )


def rollback(conn: sqlite3.Connection):
    """Remove only the seeded aliases (source='seed')."""
    try:
        conn.execute("DELETE FROM company_aliases WHERE source = 'seed'")
        print(f"{datetime.now()} - Rolled back seeded canonical aliases")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
