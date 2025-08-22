"""
Migration to backfill placeholder company names from details.name if available and not a placeholder.
"""

import sqlite3


def is_placeholder(name: str | None) -> bool:
    """Return True if name should be replaced with pretty much any other name"""
    if name is None:
        return True
    name = name.strip().lower()
    if not name:
        return True
    if name.startswith("company from"):
        return True
    if name.startswith("<unknown"):
        return True
    if name in ("unknown", "placeholder"):
        return True
    return False


def migrate(conn: sqlite3.Connection):
    from models import company_repository

    # Initialize the repository with the same database path
    repo = company_repository(db_path="data/companies.db")

    updated_count = 0
    companies = repo.get_all()
    for company in companies:
        current_name = company.name
        details_name = company.details.name if company.details else None

        updated = False

        # Condition 1: top-level name is placeholder, details name is good -> update top-level
        if (
            is_placeholder(current_name)
            and details_name
            and not is_placeholder(details_name)
        ):
            print(
                f"Updating company {company.company_id} top-level name from '{current_name}' to '{details_name}'"
            )
            company.name = details_name
            updated = True

        # Condition 2: details name is placeholder (or None) and top-level name is good -> update details
        elif not is_placeholder(current_name) and (
            details_name is None or is_placeholder(details_name)
        ):
            print(
                f"Updating company {company.company_id} details.name from '{details_name}' to '{current_name}'"
            )
            company.details.name = current_name
            updated = True

        if updated:
            try:
                repo.update(company)
                updated_count += 1
            except Exception as e:
                print(f"Error updating company {company.company_id}: {e}")

    print(f"Updated {updated_count} companies")
