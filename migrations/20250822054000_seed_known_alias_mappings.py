import sqlite3
from datetime import datetime


def migrate(conn: sqlite3.Connection):
    """Seed known alias mappings to canonical companies.

    Aliases inserted (source='seed', active=1):
      - 'aws', 'amazon web services'  -> Amazon
      - 'meta'                         -> Facebook
      - 'alphabet'                     -> Google
    """
    # Lazy import to reuse existing normalization behavior
    from models import normalize_company_name

    # Build lookup of normalized company name -> company_id
    rows = conn.execute("SELECT company_id, name FROM companies").fetchall()
    normalized_name_to_company_id: dict[str, str] = {}
    for company_id, name in rows:
        if not name:
            continue
        normalized = normalize_company_name(name)
        normalized_name_to_company_id[normalized] = company_id

    # Define mappings: alias list -> canonical company name
    mapping: list[tuple[str, list[str]]] = [
        ("Amazon", ["aws", "amazon web services"]),
        ("Facebook", ["meta"]),
        ("Google", ["alphabet"]),
    ]

    inserted = 0
    skipped = 0
    missing_targets: list[str] = []

    for canonical_name, aliases in mapping:
        canonical_norm = normalize_company_name(canonical_name)
        company_id = normalized_name_to_company_id.get(canonical_norm)
        if not company_id:
            missing_targets.append(canonical_name)
            continue

        for alias in aliases:
            norm_alias = normalize_company_name(alias)
            try:
                conn.execute(
                    """
                    INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                    VALUES (?, ?, ?, 'seed', 1)
                    """,
                    (company_id, alias, norm_alias),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1

    msg = f"{datetime.now()} - Seeded known alias mappings: inserted={inserted}, skipped={skipped}"
    if missing_targets:
        msg += f", missing_targets={','.join(missing_targets)}"
    print(msg)


def rollback(conn: sqlite3.Connection):
    """Remove only the seeded known alias mappings created by this migration."""
    try:
        conn.execute(
            "DELETE FROM company_aliases WHERE source = 'seed' AND normalized_alias IN (?, ?, ?, ?)",
            (
                # normalized('aws'), normalized('amazon web services'), normalized('meta'), normalized('alphabet')
                "aws",
                "amazon-web-services",
                "meta",
                "alphabet",
            ),
        )
        print(f"{datetime.now()} - Rolled back known alias mappings")
    except sqlite3.Error as e:
        print(f"Error during rollback: {str(e)}")
        raise
