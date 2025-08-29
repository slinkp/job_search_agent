"""Tests for the alias validation script."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from models import CompaniesSheetRow, Company, CompanyRepository, CompanyStatus
from scripts.validate_aliases import check_orphaned_aliases


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize database using the proper repository
    repo = CompanyRepository(db_path=db_path, load_sample_data=False, clear_data=True)

    yield repo

    # Cleanup
    Path(db_path).unlink()


def test_check_orphaned_aliases_no_orphans(temp_db):
    """Test that no orphaned aliases are found when all companies exist."""
    # Create a company using the model
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(),
        status=CompanyStatus(),
    )
    temp_db.create(company)

    # Create aliases for the company using the model method
    temp_db.create_alias("test-company", "Test Co", "manual")
    temp_db.create_alias("test-company", "Test Company Inc", "auto")

    orphaned = check_orphaned_aliases(temp_db.db_path)
    assert orphaned == []


def test_check_orphaned_aliases_nonexistent_company(temp_db):
    """Test that aliases for non-existent companies are detected as orphaned."""
    # Create aliases for a company that doesn't exist using raw SQL
    # This is a valid use of raw SQL since we're testing an invalid condition
    with sqlite3.connect(temp_db.db_path) as conn:
        conn.execute(
            """
            INSERT INTO company_aliases (company_id, alias, normalized_alias, source)
            VALUES (?, ?, ?, ?)
            """,
            ("nonexistent-company", "Nonexistent Co", "nonexistent-co", "auto"),
        )

    orphaned = check_orphaned_aliases(temp_db.db_path)
    assert orphaned[0]["company_id"] == "nonexistent-company"
    assert orphaned[0]["alias"] == "Nonexistent Co"
    assert orphaned[0]["source"] == "auto"
    assert len(orphaned) == 1


def test_check_orphaned_aliases_mixed_scenario(temp_db):
    """Test mixed scenario with valid and orphaned aliases."""
    # Create a valid company using the model
    valid_company = Company(
        company_id="valid-company",
        name="Valid Company",
        details=CompaniesSheetRow(),
        status=CompanyStatus(),
    )
    temp_db.create(valid_company)

    # Create a company and then soft-delete it using the model method
    deleted_company = Company(
        company_id="deleted-company",
        name="Deleted Company",
        details=CompaniesSheetRow(),
        status=CompanyStatus(),
    )
    temp_db.create(deleted_company)
    temp_db.soft_delete_company("deleted-company")

    # Create aliases for valid company using the model method
    temp_db.create_alias("valid-company", "Valid Co", "manual")

    # Create aliases for deleted company using the model method
    temp_db.create_alias("deleted-company", "Deleted Co", "auto")

    # Create aliases for non-existent company using raw SQL
    # This is a valid use of raw SQL since we're testing an invalid condition
    with sqlite3.connect(temp_db.db_path) as conn:
        conn.execute(
            """
            INSERT INTO company_aliases (company_id, alias, normalized_alias, source)
            VALUES (?, ?, ?, ?)
            """,
            ("nonexistent-company", "Nonexistent Co", "nonexistent-co", "seed"),
        )

    orphaned = check_orphaned_aliases(temp_db.db_path)

    # Check that orphaned aliases are sorted by company_id, alias
    orphaned_ids = [o["company_id"] for o in orphaned]
    assert orphaned_ids == ["nonexistent-company"]

    nonexistent_alias = next(
        o for o in orphaned if o["company_id"] == "nonexistent-company"
    )
    assert nonexistent_alias["alias"] == "Nonexistent Co"
    assert nonexistent_alias["source"] == "seed"
    assert len(orphaned) == 1
