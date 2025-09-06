import datetime
import os
import tempfile

from models import Company, CompanyRepository, CompaniesSheetRow, RecruiterMessage


def test_merge_allows_deleted_duplicate():
    # Use a temporary file-backed DB to ensure a single database across connections
    fd, db_path = tempfile.mkstemp(prefix="test_db_", suffix=".sqlite")
    os.close(fd)
    try:
        repo = CompanyRepository(db_path=db_path, load_sample_data=False, clear_data=True)

        # Create canonical and duplicate companies
        canonical = Company(
            company_id="canonical",
            name="Homeaglow",
            details=CompaniesSheetRow(name="Homeaglow"),
        )
        duplicate = Company(
            company_id="duplicate",
            name="Home Aglow",
            details=CompaniesSheetRow(name="Home Aglow"),
        )
        repo.create(canonical)
        repo.create(duplicate)

        # Add alias and message to duplicate to verify they migrate
        repo.create_alias("duplicate", "Home Aglow Inc.", "manual")
        msg = RecruiterMessage(
            message_id="m1",
            company_id="duplicate",
            thread_id="t1",
            message="hello",
            date=datetime.datetime.now(datetime.timezone.utc),
        )
        repo.create_recruiter_message(msg)

        # Soft delete the duplicate before merging
        assert repo.soft_delete_company("duplicate") is True

        # Should still be able to merge into canonical
        assert repo.merge_companies("canonical", "duplicate") is True

        # Alias from duplicate should now be on canonical
        aliases = repo.list_aliases("canonical")
        assert any(a["alias"] == "Home Aglow Inc." for a in aliases)

        # Message should be repointed to canonical
        messages = repo.get_recruiter_messages("canonical")
        assert any(m.message_id == "m1" for m in messages)

        # Duplicate remains soft-deleted
        with repo._get_connection() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "SELECT deleted_at FROM companies WHERE company_id = ?", ("duplicate",)
            ).fetchone()
            assert row and row[0] is not None
    finally:
        try:
            os.remove(db_path)
        except FileNotFoundError:
            pass
