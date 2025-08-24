import datetime
import json
import os
import sqlite3
from datetime import date

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from models import (
    CompaniesSheetRow,
    Company,
    CompanyRepository,
    CompanyStatus,
    CustomJSONEncoder,
    Event,
    EventType,
    FitCategory,
    RecruiterMessage,
    company_repository,
    is_placeholder,
    merge_company_data,
    normalize_company_name,
)

TEST_DB_PATH = "data/_test_companies.db"


@pytest.fixture(scope="function")
def clean_test_db():
    """Ensure we have a clean test database for each test."""
    # Remove the test database if it exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Make sure the directory exists
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)

    # Create a new repository with the test database
    repo = CompanyRepository(db_path=TEST_DB_PATH, clear_data=True)

    yield repo

    # Clean up after the test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


class TestCompanyRepository:

    def test_create_and_get_company(self, clean_test_db):
        """Test creating and retrieving a company."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
                type="Private",
                url="https://testcompany.example.com",
            ),
            reply_message="Test reply",
        )

        # Save it to the database
        created_company = repo.create(company)

        # Verify it was created with the correct data
        assert created_company.company_id == "test-company"
        assert created_company.name == "TestCompany"
        assert created_company.details.name == "TestCompany"
        assert created_company.details.type == "Private"
        assert created_company.details.url == "https://testcompany.example.com"
        assert created_company.reply_message == "Test reply"

        # Retrieve it from the database
        retrieved_company = repo.get("test-company")

        # Verify it matches what we created
        assert retrieved_company is not None
        assert retrieved_company.company_id == created_company.company_id
        assert retrieved_company.name == created_company.name
        assert retrieved_company.details.name == created_company.details.name
        assert retrieved_company.details.type == created_company.details.type
        assert retrieved_company.details.url == created_company.details.url
        assert retrieved_company.reply_message == created_company.reply_message

    def test_update_company(self, clean_test_db):
        """Test updating a company."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
                type="Private",
            ),
            reply_message="Original reply",
        )

        # Save it to the database
        repo.create(company)

        # Modify the company
        company.details.type = "Public"
        company.reply_message = "Updated reply"

        # Update it in the database
        updated_company = repo.update(company)

        # Verify it was updated
        assert updated_company.details.type == "Public"
        assert updated_company.reply_message == "Updated reply"

        # Retrieve it again to confirm the update persisted
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None
        assert retrieved_company.details.type == "Public"
        assert retrieved_company.reply_message == "Updated reply"

    def test_delete_company(self, clean_test_db):
        """Test deleting a company."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
            ),
        )

        # Save it to the database
        repo.create(company)

        # Verify it exists
        assert repo.get("test-company") is not None

        # Delete it
        repo.delete("test-company")

        # Verify it no longer exists
        assert repo.get("test-company") is None

    def test_get_all_companies(self, clean_test_db):
        """Test retrieving all companies."""
        repo = clean_test_db

        # Create multiple test companies
        companies = [
            Company(
                company_id=f"test-company-{i}",
                name=f"TestCompany{i}",
                details=CompaniesSheetRow(
                    name=f"TestCompany{i}",
                    type=f"Type{i}",
                ),
            )
            for i in range(3)
        ]

        # Save them to the database
        for company in companies:
            repo.create(company)

        # Retrieve all companies
        all_companies = repo.get_all()

        # Verify we got all of them
        assert len(all_companies) == 3
        company_ids = {company.company_id for company in all_companies}
        assert company_ids == {"test-company-0", "test-company-1", "test-company-2"}

    def test_company_with_recruiter_message(self, clean_test_db):
        """Test creating and retrieving a company with a recruiter message."""
        repo = clean_test_db

        # Create a test recruiter message
        recruiter_message = RecruiterMessage(
            message_id="test123",
            company_id="test-company",
            message="Hello, we have a job opportunity for you.",
            subject="Job Opportunity",
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread123",
            thread_id="thread123",
            date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )

        # Create a test company with the recruiter message
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
                type="Private",
            ),
            recruiter_message=recruiter_message,
        )

        # Save it to the database
        created_company = repo.create(company)

        # Verify the company was created
        assert created_company.company_id == "test-company"

        # Retrieve the company with the recruiter message
        retrieved_company = repo.get("test-company")

        # Verify the recruiter message was saved and retrieved correctly
        assert retrieved_company is not None
        assert retrieved_company.company_id == "test-company"
        assert retrieved_company.recruiter_message is not None
        assert retrieved_company.recruiter_message.message_id == "test123"
        assert (
            retrieved_company.recruiter_message.message
            == "Hello, we have a job opportunity for you."
        )

    @pytest.fixture
    def companies_for_name_search(self, clean_test_db):
        """Fixture to create test companies for normalized name search tests."""
        repo = clean_test_db

        # Create a test company
        company1 = Company(
            company_id="test-company-1",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company", type="Private"),
        )
        repo.create(company1)

        # Create another test company with a different name pattern
        company2 = Company(
            company_id="test-company-2",
            name="TestCompany With   Multiple   Spaces",
            details=CompaniesSheetRow(name="TestCompany With   Multiple   Spaces"),
        )
        repo.create(company2)

        return repo

    @pytest.mark.parametrize(
        "search_name, expected_company_id, should_find",
        [
            # Exact match
            ("Test Company", "test-company-1", True),
            # Different case and extra spaces
            ("  tEsT   cOMpany  ", "test-company-1", True),
            # Normalized form (hyphens instead of spaces)
            ("test-company", "test-company-1", True),
            # Company 2 using normalized form
            ("testcompany-with-multiple-spaces", "test-company-2", True),
            # Non-existent company
            ("Non Existent Company", None, False),
        ],
    )
    def test_get_by_normalized_name(
        self, companies_for_name_search, search_name, expected_company_id, should_find
    ):
        """Test getting a company by normalized name with various input formats."""
        repo = companies_for_name_search

        # Search for the company
        found_company = repo.get_by_normalized_name(search_name)

        if should_find:
            assert (
                found_company is not None
            ), f"Should have found company with name '{search_name}'"
            assert normalize_company_name(found_company.name) == normalize_company_name(
                search_name
            )
            assert found_company.company_id == expected_company_id
        else:
            assert (
                found_company is None
            ), f"Should not have found company with name '{search_name}', found with {found_company.name}"

    def test_company_repository_singleton(self):
        """Test that the company_repository function returns a singleton."""
        # Remove the test database if it exists
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

        # Get two repository instances with the same path
        repo1 = company_repository(db_path=TEST_DB_PATH)
        repo2 = company_repository(db_path=TEST_DB_PATH)

        # Verify they are the same instance
        assert repo1 is repo2

        # Clean up
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_update_company_with_recruiter_message(self, clean_test_db):
        """Test updating a company that has a recruiter message."""
        repo = clean_test_db

        # Create a test recruiter message
        recruiter_message = RecruiterMessage(
            message_id="test123",
            message="Hello, we have a job opportunity for you.",
            subject="Job Opportunity",
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread123",
            thread_id="thread123",
            date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )

        # Create a test company with the recruiter message
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
                type="Private",
            ),
            recruiter_message=recruiter_message,
        )

        # Save it to the database
        created_company = repo.create(company)

        # Modify the recruiter message
        created_company.recruiter_message.subject = "Updated Job Opportunity"
        created_company.recruiter_message.message = "Updated message content"
        created_company.details.type = "Public"

        # Update the company
        repo.update(created_company)

        # Retrieve the company again
        retrieved_company = repo.get("test-company")

        # Verify the company and recruiter message were updated correctly
        assert retrieved_company is not None
        assert retrieved_company.details.type == "Public"
        assert retrieved_company.recruiter_message is not None
        assert retrieved_company.recruiter_message.subject == "Updated Job Opportunity"
        assert retrieved_company.recruiter_message.message == "Updated message content"
        assert retrieved_company.recruiter_message.message_id == "test123"

    def test_get_all_messages(self, clean_test_db):
        """Test the get_all_messages method returns all messages with company info."""
        repo = clean_test_db

        # Create multiple companies with messages
        company1 = Company(
            company_id="test-corp-1",
            name="Test Corp 1",
            details=CompaniesSheetRow(name="Test Corp 1"),
            status=CompanyStatus(),
        )
        repo.create(company1)

        company2 = Company(
            company_id="test-corp-2",
            name="Test Corp 2",
            details=CompaniesSheetRow(name="Test Corp 2"),
            status=CompanyStatus(),
        )
        repo.create(company2)

        # Create messages for both companies
        message1 = RecruiterMessage(
            message_id="msg-1",
            company_id="test-corp-1",
            subject="Test Subject 1",
            sender="recruiter1@test.com",
            date=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            message="Test message content 1",
            email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread1",
            thread_id="thread1",
        )
        repo.create_recruiter_message(message1)

        message2 = RecruiterMessage(
            message_id="msg-2",
            company_id="test-corp-2",
            subject="Test Subject 2",
            sender="recruiter2@test.com",
            date=datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc),
            message="Test message content 2",
            email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread2",
            thread_id="thread2",
        )
        repo.create_recruiter_message(message2)

        # Get all messages
        all_messages = repo.get_all_messages()

        # Verify we got all messages
        assert isinstance(all_messages, list)
        assert len(all_messages) == 2

        # Verify messages are RecruiterMessage objects
        assert all(isinstance(msg, RecruiterMessage) for msg in all_messages)

        # Verify messages are ordered by date (newest first)
        assert all_messages[0].message_id == "msg-2"  # Newer date
        assert all_messages[1].message_id == "msg-1"  # Older date

        # Verify message content
        msg1 = next(msg for msg in all_messages if msg.message_id == "msg-1")
        assert msg1.company_id == "test-corp-1"
        assert msg1.subject == "Test Subject 1"
        assert msg1.sender == "recruiter1@test.com"
        assert msg1.message == "Test message content 1"
        assert getattr(msg1, "_company_name") == "Test Corp 1"

        msg2 = next(msg for msg in all_messages if msg.message_id == "msg-2")
        assert msg2.company_id == "test-corp-2"
        assert msg2.subject == "Test Subject 2"
        assert msg2.sender == "recruiter2@test.com"
        assert msg2.message == "Test message content 2"
        assert getattr(msg2, "_company_name") == "Test Corp 2"

    def test_get_all_messages_empty(self, clean_test_db):
        """Test get_all_messages returns empty list when no messages exist."""
        repo = clean_test_db

        # Create a company without any messages
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
        )
        repo.create(company)

        # Get all messages
        all_messages = repo.get_all_messages()

        # Verify empty result
        assert isinstance(all_messages, list)
        assert len(all_messages) == 0

    def test_get_all_messages_with_archived_messages(self, clean_test_db):
        """Test get_all_messages includes archived messages."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
        )
        repo.create(company)

        # Create a message and archive it
        message = RecruiterMessage(
            message_id="archived-msg",
            company_id="test-company",
            subject="Archived Message",
            sender="recruiter@test.com",
            date=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            message="This message is archived",
            email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread1",
            thread_id="thread1",
            archived_at=datetime.datetime(
                2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
            ),
        )
        repo.create_recruiter_message(message)

        # Get all messages
        all_messages = repo.get_all_messages()

        # Verify archived message is included
        assert len(all_messages) == 1
        assert all_messages[0].message_id == "archived-msg"
        assert all_messages[0].archived_at is not None
        assert getattr(all_messages[0], "_company_name") == "Test Company"

    def test_alias_resolution_multiple_aliases(self, clean_test_db):
        """Active aliases resolve to the canonical company via get_by_normalized_name."""
        repo = clean_test_db

        # Create canonical company
        company = Company(
            company_id="amazon",
            name="Amazon",
            details=CompaniesSheetRow(name="Amazon"),
        )
        repo.create(company)

        # Seed multiple aliases
        aliases = ["aws", "amazon web services"]
        with repo._get_connection() as conn:  # type: ignore[attr-defined]
            for alias in aliases:
                conn.execute(
                    """
                    INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                    VALUES (?, ?, ?, 'manual', 1)
                    """,
                    (company.company_id, alias, normalize_company_name(alias)),
                )
            conn.commit()

        # Both aliases should resolve
        found_aws = repo.get_by_normalized_name("AWS")
        assert found_aws is not None and found_aws.company_id == "amazon"
        found_long = repo.get_by_normalized_name("Amazon Web Services")
        assert found_long is not None and found_long.company_id == "amazon"

    def test_alias_inactive_ignored(self, clean_test_db):
        """Inactive aliases should not resolve."""
        repo = clean_test_db

        company = Company(
            company_id="meta",
            name="Facebook",
            details=CompaniesSheetRow(name="Facebook"),
        )
        repo.create(company)

        with repo._get_connection() as conn:  # type: ignore[attr-defined]
            conn.execute(
                """
                INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                VALUES (?, ?, ?, 'manual', 0)
                """,
                (company.company_id, "Meta", normalize_company_name("Meta")),
            )
            conn.commit()

        # Should not resolve because alias is inactive
        assert repo.get_by_normalized_name("meta") is None

    def test_alias_uniqueness_enforced_for_active(self, clean_test_db):
        """Unique constraint prevents duplicate active aliases for the same company."""
        repo = clean_test_db

        company = Company(
            company_id="google",
            name="Google",
            details=CompaniesSheetRow(name="Google"),
        )
        repo.create(company)

        with repo._get_connection() as conn:  # type: ignore[attr-defined]
            # First insert should work
            conn.execute(
                """
                INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                VALUES (?, ?, ?, 'manual', 1)
                """,
                (company.company_id, "Alphabet", normalize_company_name("Alphabet")),
            )
            conn.commit()

            # Second insert with same normalized_alias for same company and active=1 should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO company_aliases (company_id, alias, normalized_alias, source, is_active)
                    VALUES (?, ?, ?, 'manual', 1)
                    """,
                    (
                        company.company_id,
                        "ALPHABET",  # different case, same normalized
                        normalize_company_name("Alphabet"),
                    ),
                )

    def test_create_alias_success(self, clean_test_db):
        """Test creating a new alias for a company."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create an alias
        alias_id = repo.create_alias("test-company", "Test Corp", "manual")

        # Verify the alias was created
        assert alias_id is not None
        assert isinstance(alias_id, int)

        # Get the alias and verify its data
        alias = repo.get_alias(alias_id)
        assert alias is not None
        assert alias["company_id"] == "test-company"
        assert alias["alias"] == "Test Corp"
        assert alias["normalized_alias"] == "test-corp"
        assert alias["source"] == "manual"
        assert alias["is_active"] is True

    def test_create_alias_duplicate_fails(self, clean_test_db):
        """Test that creating a duplicate alias fails."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create first alias
        repo.create_alias("test-company", "Test Corp", "manual")

        # Try to create duplicate alias
        with pytest.raises(sqlite3.IntegrityError):
            repo.create_alias("test-company", "Test Corp", "manual")

    def test_get_alias_not_found(self, clean_test_db):
        """Test getting a non-existent alias."""
        repo = clean_test_db

        # Try to get non-existent alias
        alias = repo.get_alias(999)
        assert alias is None

    def test_update_alias_success(self, clean_test_db):
        """Test updating an existing alias."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create an alias
        alias_id = repo.create_alias("test-company", "Test Corp", "manual")

        # Update the alias
        updated_alias = repo.update_alias(alias_id, alias="Updated Corp", is_active=False)

        # Verify the alias was updated
        assert updated_alias is not None
        assert updated_alias["alias"] == "Updated Corp"
        assert updated_alias["normalized_alias"] == "updated-corp"
        assert updated_alias["is_active"] is False

    def test_update_alias_not_found(self, clean_test_db):
        """Test updating a non-existent alias."""
        repo = clean_test_db

        # Try to update non-existent alias
        updated_alias = repo.update_alias(999, alias="New Name")
        assert updated_alias is None

    def test_deactivate_alias_success(self, clean_test_db):
        """Test deactivating an alias."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create an alias
        alias_id = repo.create_alias("test-company", "Test Corp", "manual")

        # Deactivate the alias
        success = repo.deactivate_alias(alias_id)

        # Verify the alias was deactivated
        assert success is True

        # Verify the alias is now inactive
        alias = repo.get_alias(alias_id)
        assert alias is not None
        assert alias["is_active"] is False

    def test_deactivate_alias_not_found(self, clean_test_db):
        """Test deactivating a non-existent alias."""
        repo = clean_test_db

        # Try to deactivate non-existent alias
        success = repo.deactivate_alias(999)
        assert success is False

    def test_set_alias_as_canonical_success(self, clean_test_db):
        """Test setting an alias as the canonical name."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="Original Name",
            details=CompaniesSheetRow(name="Original Name"),
        )
        repo.create(company)

        # Create an alias
        alias_id = repo.create_alias("test-company", "New Canonical Name", "manual")

        # Set the alias as canonical
        success = repo.set_alias_as_canonical("test-company", alias_id)

        # Verify it was successful
        assert success is True

        # Verify the company name was updated
        updated_company = repo.get("test-company")
        assert updated_company is not None
        assert updated_company.name == "New Canonical Name"
        assert updated_company.details.name == "New Canonical Name"

        # Verify the old name was preserved as an alias
        updated_company_with_aliases = repo.get("test-company", include_aliases=True)
        aliases = getattr(updated_company_with_aliases, "_aliases", [])
        old_name_aliases = [a for a in aliases if a["alias"] == "Original Name"]
        assert len(old_name_aliases) == 1
        assert old_name_aliases[0]["source"] == "seed"

    def test_set_alias_as_canonical_not_found(self, clean_test_db):
        """Test setting a non-existent alias as canonical."""
        repo = clean_test_db

        # Create a test company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Try to set non-existent alias as canonical
        success = repo.set_alias_as_canonical("test-company", 999)
        assert success is False

    def test_set_alias_as_canonical_wrong_company(self, clean_test_db):
        """Test setting an alias as canonical for the wrong company."""
        repo = clean_test_db

        # Create two test companies
        company1 = Company(
            company_id="company-1",
            name="Company 1",
            details=CompaniesSheetRow(name="Company 1"),
        )
        repo.create(company1)

        company2 = Company(
            company_id="company-2",
            name="Company 2",
            details=CompaniesSheetRow(name="Company 2"),
        )
        repo.create(company2)

        # Create an alias for company 1
        alias_id = repo.create_alias("company-1", "Alias for Company 1", "manual")

        # Try to set it as canonical for company 2
        success = repo.set_alias_as_canonical("company-2", alias_id)
        assert success is False


class TestCompaniesSheetRow:

    def test_company_identifier(self):
        """Test the company_identifier property."""
        # With both name and URL
        row = CompaniesSheetRow(
            name="TestCompany",
            url="https://example.com",
        )
        assert row.company_identifier == "TestCompany at https://example.com"

        # With only name
        row = CompaniesSheetRow(
            name="TestCompany",
        )
        assert row.company_identifier == "TestCompany"

        # With only URL
        row = CompaniesSheetRow(
            url="https://example.com",
        )
        assert row.company_identifier == "with unknown name at https://example.com"

        # With neither
        row = CompaniesSheetRow()
        assert row.company_identifier == ""


class TestEvents:

    @pytest.fixture
    def event_repo(self, tmp_path):
        """Create a test repository with a temporary database."""
        # Use a temporary file for the database
        db_path = tmp_path / "test_events.db"

        # Create a repository with a clean database
        repo = CompanyRepository(db_path=str(db_path), clear_data=True)

        # Create a test company
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
            reply_message="Test reply",
        )
        repo.create(company)

        return repo

    def test_create_event(self, event_repo):
        """Test creating an event."""
        # Create an event
        event = Event(company_id="test-company", event_type=EventType.REPLY_SENT)
        created_event = event_repo.create_event(event)

        # Verify the event was created with an ID and timestamp
        assert created_event.id is not None
        assert created_event.timestamp is not None
        assert created_event.company_id == "test-company"
        assert created_event.event_type == EventType.REPLY_SENT

    def test_get_events_by_company(self, event_repo):
        """Test retrieving events filtered by company."""
        # Create multiple events for the same company
        event1 = event_repo.create_event(
            Event(
                company_id="test-company",
                event_type=EventType.COMPANY_CREATED,
                timestamp=datetime.datetime(
                    2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            )
        )

        event2 = event_repo.create_event(
            Event(
                company_id="test-company",
                event_type=EventType.RESEARCH_COMPLETED,
                timestamp=datetime.datetime(
                    2023, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            )
        )

        # Get events for the company
        events = event_repo.get_events(company_id="test-company")

        # Verify we got both events, sorted by timestamp (newest first)
        assert len(events) == 2
        assert events[0].id == event2.id  # Newest first
        assert events[1].id == event1.id

    def test_get_events_by_type(self, event_repo):
        """Test retrieving events filtered by type."""
        # Create events of different types
        event_repo.create_event(
            Event(company_id="test-company", event_type=EventType.COMPANY_CREATED)
        )

        event_repo.create_event(
            Event(company_id="test-company", event_type=EventType.RESEARCH_COMPLETED)
        )

        # Get only research completed events
        events = event_repo.get_events(event_type=EventType.RESEARCH_COMPLETED)

        # Verify we got only the research event
        assert len(events) == 1
        assert events[0].event_type == EventType.RESEARCH_COMPLETED

    def test_get_events_by_company_and_type(self, event_repo):
        """Test retrieving events filtered by both company and type."""
        # Create events for different companies
        event_repo.create(
            Company(
                company_id="another-company",
                name="Another Company",
                details=CompaniesSheetRow(name="Another Company"),
            )
        )

        event_repo.create_event(
            Event(company_id="test-company", event_type=EventType.REPLY_SENT)
        )

        event_repo.create_event(
            Event(company_id="another-company", event_type=EventType.REPLY_SENT)
        )

        event_repo.create_event(
            Event(company_id="test-company", event_type=EventType.RESEARCH_COMPLETED)
        )

        # Get only reply events for Test Company
        events = event_repo.get_events(
            company_id="test-company", event_type=EventType.REPLY_SENT
        )

        # Verify we got only the matching event
        assert len(events) == 1
        assert events[0].company_id == "test-company"
        assert events[0].event_type == EventType.REPLY_SENT

    def test_event_serialization(self):
        """Test serialization of Event objects."""
        # Create an event with a specific timestamp
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event = Event(
            id=1,
            company_id="test-company",
            event_type=EventType.REPLY_SENT,
            timestamp=timestamp,
        )

        # Use the CustomJSONEncoder to serialize the event
        encoder = CustomJSONEncoder()
        serialized_str = encoder.encode(event)
        serialized = json.loads(serialized_str)

        # Verify the serialized format
        assert serialized["id"] == 1
        assert serialized["company_id"] == "test-company"
        assert serialized["event_type"] == "reply_sent"
        assert serialized["timestamp"] == "2023-01-01T12:00:00+00:00"

    def test_from_list(self):
        """Test creating a CompaniesSheetRow from a list of strings."""
        # Create a list with values for the first few fields
        row_data = [
            "TestCompany",
            "Private",
            "100M",
            "Series B",
            "yes",
            "https://example.com",
        ]

        # Pad with empty strings for the remaining fields
        field_count = len(CompaniesSheetRow.model_fields)
        row_data.extend([""] * (field_count - len(row_data)))

        # Create a CompaniesSheetRow from the list
        row = CompaniesSheetRow.from_list(row_data)

        # Verify the values were set correctly
        assert row.name == "TestCompany"
        assert row.type == "Private"
        assert row.valuation == "100M"
        assert row.funding_series == "Series B"
        assert row.rc is True
        assert row.url == "https://example.com"


class TestCompany:

    def test_company_properties(self):
        """Test the properties of the Company class."""
        # Create a company with a recruiter message
        recruiter_message = RecruiterMessage(
            message_id="test123",
            message="Hello, we have a job opportunity for you.",
            email_thread_link="https://mail.example.com/thread123",
            thread_id="thread123",
        )

        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
            ),
            recruiter_message=recruiter_message,
        )

        # Test the properties
        assert company.email_thread_link == "https://mail.example.com/thread123"
        assert company.thread_id == "thread123"
        assert company.initial_message == "Hello, we have a job opportunity for you."

        # Test setting the initial_message
        company.initial_message = "Updated message"
        assert company.recruiter_message is not None
        assert company.recruiter_message.message == "Updated message"

        # Test with no recruiter message
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
            ),
        )

        assert company.email_thread_link == ""
        assert company.thread_id == ""
        assert company.initial_message == ""

        # Test setting initial_message when no recruiter message exists
        company.initial_message = "New message"
        assert company.recruiter_message is not None
        assert company.recruiter_message.message == "New message"


@pytest.mark.parametrize(
    "input_name, expected_output",
    [
        ("Test Company", "test-company"),
        ("  Test   Company  ", "test-company"),
        ("TEST COMPANY", "test-company"),
        ("test company", "test-company"),
        (" TestCo ", "testco"),
        ("Another Multi Word Name", "another-multi-word-name"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_company_name(input_name, expected_output):
    """Test the company name normalization function."""
    assert normalize_company_name(input_name) == expected_output


@freeze_time("2023-01-15")
def test_merge_company_data_basic():
    """Test merging data from spreadsheet to existing company - basic case."""
    # Create existing company with initial data
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            type="Tech",
            valuation="500M",
            funding_series="Series A",
            url="test.com",
            updated=date(2022, 12, 1),
        ),
        status=CompanyStatus(),
    )

    # Create spreadsheet row with updated data
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        type="AI",  # Changed
        valuation="1B",  # Changed
        funding_series="Series B",  # Changed
        headquarters="San Francisco",  # New field
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify spreadsheet values were used for non-empty fields
    assert merged_company.details.type == "AI"
    assert merged_company.details.valuation == "1B"
    assert merged_company.details.funding_series == "Series B"
    assert merged_company.details.headquarters == "San Francisco"

    # Verify database values were preserved for fields not in spreadsheet
    assert merged_company.details.url == "test.com"

    # Verify existing updated date is preserved when spreadsheet has no updated date
    assert merged_company.details.updated == date(2022, 12, 1)


@freeze_time("2023-01-15")
def test_merge_company_data_empty_values():
    """Test merging data with empty values in spreadsheet."""
    # Create existing company with initial data
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            type="Tech",
            valuation="500M",
            url="test.com",
        ),
        status=CompanyStatus(),
    )

    # Create spreadsheet row with some empty values
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        type="",  # Empty
        valuation="1B",  # Changed
        url=None,  # None/null
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify empty spreadsheet values don't override existing values
    assert merged_company.details.type == "Tech"  # Preserved
    assert merged_company.details.valuation == "1B"  # Updated
    assert merged_company.details.url == "test.com"  # Preserved


@freeze_time("2023-01-15")
def test_merge_company_data_date_fields():
    """Test merging data with date fields."""
    # Create existing company with initial data
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            started=date(2018, 5, 10),  # Older date
            end_date=date(2022, 3, 15),  # Newer date
            updated=date(2022, 12, 1),
        ),
        status=CompanyStatus(),
    )

    # Create spreadsheet row with date fields
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        started=date(2020, 1, 1),  # Newer date than existing
        end_date=date(2021, 10, 5),  # Older date than existing
        updated=date(2023, 1, 10),  # Newer date than existing
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify the most recent date is used
    assert merged_company.details.started == date(2020, 1, 1)
    assert merged_company.details.end_date == date(2022, 3, 15)
    assert merged_company.details.updated == date(2023, 1, 10)

    # Now test with newer updated date in spreadsheet
    # Create a fresh company for this test case to avoid state from previous test
    existing_company_newer = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            updated=date(2022, 12, 1),
        ),
        status=CompanyStatus(),
    )

    sheet_row_with_newer_date = CompaniesSheetRow(
        name="Test Corp",
        updated=date(2023, 1, 10),  # Newer date than existing
    )

    merged_company = merge_company_data(existing_company_newer, sheet_row_with_newer_date)
    # Should use the newer date from the spreadsheet
    assert merged_company.details.updated == date(2023, 1, 10)

    # Test with older updated date in spreadsheet
    # Create a fresh company for this test case to avoid state from previous test
    existing_company_older = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            updated=date(2022, 12, 1),
        ),
        status=CompanyStatus(),
    )

    sheet_row_with_older_date = CompaniesSheetRow(
        name="Test Corp",
        updated=date(2022, 11, 1),  # Older date than existing
    )

    merged_company = merge_company_data(existing_company_older, sheet_row_with_older_date)
    # Should keep the newer date from the DB
    assert merged_company.details.updated == date(2022, 12, 1)

    # Test with no existing updated date but spreadsheet has one
    existing_company_no_updated = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            started=date(2018, 5, 10),
        ),
        status=CompanyStatus(),
    )
    merged_company = merge_company_data(
        existing_company_no_updated, sheet_row_with_older_date
    )
    # Should use the spreadsheet date
    assert merged_company.details.updated == date(2022, 11, 1)

    # Test with neither having updated date - should use today
    sheet_no_date = CompaniesSheetRow(name="Test Corp")

    # Create a fresh company with no updated date for the final test
    existing_company_no_date = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
        ),
        status=CompanyStatus(),
    )

    merged_company = merge_company_data(existing_company_no_date, sheet_no_date)
    # Should use today's date (which is frozen to 2023-01-15)
    assert merged_company.details.updated == date(2023, 1, 15)


@freeze_time("2023-01-15")
def test_merge_company_data_notes_field():
    """Test merging data with notes field."""
    # Create existing company with notes
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            notes="Original notes from database",
        ),
        status=CompanyStatus(),
    )

    # Create spreadsheet row with notes
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        notes="Additional notes from spreadsheet",
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify notes were appended, not replaced
    assert merged_company.details.notes is not None
    assert "Original notes from database" in merged_company.details.notes
    assert "Additional notes from spreadsheet" in merged_company.details.notes

    # Verify there's a separator
    assert "\n---\n" in merged_company.details.notes


@freeze_time("2023-01-15")
def test_merge_company_data_empty_notes():
    """Test merging data with empty notes field."""
    # Existing company with notes
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            notes="Original notes",
        ),
        status=CompanyStatus(),
    )

    # Spreadsheet row with empty notes
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        notes="",
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify original notes are preserved
    assert merged_company.details.notes == "Original notes"

    # Empty DB notes, non-empty sheet notes
    existing_company.details.notes = ""
    sheet_row.notes = "New notes"

    merged_company = merge_company_data(existing_company, sheet_row)
    assert merged_company.details.notes == "New notes"


def test_company_status_import_tracking():
    """Test that the CompanyStatus class properly tracks import information."""
    # Create a new CompanyStatus with default values
    status = CompanyStatus()
    assert status.imported_from_spreadsheet is False
    assert status.imported_at is None

    # Create a CompanyStatus with import information
    import_time = datetime.datetime.now(datetime.timezone.utc)
    status = CompanyStatus(imported_from_spreadsheet=True, imported_at=import_time)

    # Test serialization includes the new fields
    status_dict = status.model_dump()
    assert "imported_from_spreadsheet" in status_dict
    assert status_dict["imported_from_spreadsheet"] is True
    assert "imported_at" in status_dict
    assert status_dict["imported_at"] == import_time


def test_company_status_fit_decision():
    """Test company fit decision fields validation and serialization."""

    # Test valid fit decision
    status = CompanyStatus(
        fit_category=FitCategory.GOOD,
        fit_confidence_score=0.9,
        fit_decision_timestamp=datetime.datetime(
            2024, 1, 1, tzinfo=datetime.timezone.utc
        ),
        fit_features_used=["compensation", "location", "company_size"],
    )
    assert status.fit_category == FitCategory.GOOD
    assert status.fit_confidence_score == 0.9
    assert status.fit_features_used == ["compensation", "location", "company_size"]
    assert status.has_fit_decision is True

    # Test serialization/deserialization
    json_data = json.dumps(status.model_dump(), cls=CustomJSONEncoder)
    loaded_status = CompanyStatus.model_validate_json(json_data)
    assert loaded_status.fit_category == status.fit_category
    assert loaded_status.fit_confidence_score == status.fit_confidence_score
    assert loaded_status.fit_features_used == status.fit_features_used
    assert loaded_status.fit_decision_timestamp == status.fit_decision_timestamp

    # Test validation of invalid category
    with pytest.raises(ValidationError) as exc_info:
        CompanyStatus(fit_category="invalid")  # type: ignore
    assert "Input should be 'good', 'bad' or 'needs_more_info'" in str(exc_info.value)

    # Test confidence score range validation
    with pytest.raises(ValidationError) as exc_info:
        CompanyStatus(fit_confidence_score=-0.1)
    assert "Input should be greater than or equal to 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        CompanyStatus(fit_confidence_score=1.1)
    assert "Input should be less than or equal to 1" in str(exc_info.value)

    # Test empty status
    empty_status = CompanyStatus()
    assert empty_status.fit_category is None
    assert empty_status.fit_confidence_score is None
    assert empty_status.fit_features_used == []
    assert empty_status.has_fit_decision is False

    # Test partial fit decision validation
    with pytest.raises(ValueError) as exc_info:
        CompanyStatus(fit_category=FitCategory.GOOD)
    assert "fit_confidence_score is required when fit_category is set" in str(
        exc_info.value
    )

    with pytest.raises(ValueError) as exc_info:
        CompanyStatus(fit_category=FitCategory.GOOD, fit_confidence_score=0.9)
    assert "fit_decision_timestamp is required when fit_category is set" in str(
        exc_info.value
    )

    # Test needs more info category
    needs_info_status = CompanyStatus(
        fit_category=FitCategory.NEEDS_MORE_INFO,
        fit_confidence_score=1.0,
        fit_decision_timestamp=datetime.datetime(
            2024, 1, 1, tzinfo=datetime.timezone.utc
        ),
        fit_features_used=["compensation"],
    )
    assert needs_info_status.fit_category == FitCategory.NEEDS_MORE_INFO
    assert needs_info_status.has_fit_decision is True


@freeze_time("2023-01-15")
def test_merge_company_data_preserves_fit_decision():
    """Test that merging data preserves fit decision information."""
    # Create existing company with fit decision
    existing_company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(
            name="Test Corp",
            type="Tech",
            valuation="500M",
        ),
        status=CompanyStatus(
            fit_category=FitCategory.GOOD,
            fit_confidence_score=0.9,
            fit_decision_timestamp=datetime.datetime(
                2024, 1, 1, tzinfo=datetime.timezone.utc
            ),
            fit_features_used=["compensation", "location"],
        ),
    )

    # Create spreadsheet row with updated data
    sheet_row = CompaniesSheetRow(
        name="Test Corp",
        type="AI",  # Changed
        valuation="1B",  # Changed
        headquarters="San Francisco",  # New field
    )

    # Merge data
    merged_company = merge_company_data(existing_company, sheet_row)

    # Verify fit decision was preserved
    assert merged_company.status.fit_category == FitCategory.GOOD
    assert merged_company.status.fit_confidence_score == 0.9
    assert merged_company.status.fit_decision_timestamp == datetime.datetime(
        2024, 1, 1, tzinfo=datetime.timezone.utc
    )
    assert merged_company.status.fit_features_used == ["compensation", "location"]

    # Also verify the spreadsheet data was merged correctly
    assert merged_company.details.type == "AI"
    assert merged_company.details.valuation == "1B"
    assert merged_company.details.headquarters == "San Francisco"


class TestCompanyMessages:
    """Test the new messages property and related functionality."""

    def test_company_messages_property_empty(self, clean_test_db):
        """Test that messages property returns empty list when no messages exist."""
        repo = clean_test_db

        # Create a company without any messages
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Retrieve the company
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None

        # Test that messages property returns empty list
        messages = retrieved_company.messages
        assert isinstance(messages, list)
        assert len(messages) == 0

    def test_company_messages_property_single_message(self, clean_test_db):
        """Test that messages property returns single message when one exists."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create a recruiter message
        message = RecruiterMessage(
            message_id="msg1",
            company_id="test-company",
            message="Hello, we have a job opportunity for you.",
            subject="Job Opportunity",
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread1",
            thread_id="thread1",
            date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )
        repo.create_recruiter_message(message)

        # Retrieve the company
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None

        # Test that messages property returns the message
        messages = retrieved_company.messages
        assert isinstance(messages, list)
        assert len(messages) == 1
        assert messages[0].message_id == "msg1"
        assert messages[0].subject == "Job Opportunity"
        assert messages[0].sender == "recruiter@example.com"

    def test_company_messages_property_multiple_messages(self, clean_test_db):
        """Test that messages property returns multiple messages in date order."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create multiple recruiter messages with different dates
        messages = [
            RecruiterMessage(
                message_id="msg1",
                company_id="test-company",
                message="First message",
                subject="First",
                sender="recruiter1@example.com",
                email_thread_link="https://mail.example.com/thread1",
                thread_id="thread1",
                date=datetime.datetime(
                    2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
            RecruiterMessage(
                message_id="msg2",
                company_id="test-company",
                message="Second message",
                subject="Second",
                sender="recruiter2@example.com",
                email_thread_link="https://mail.example.com/thread2",
                thread_id="thread2",
                date=datetime.datetime(
                    2023, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
            RecruiterMessage(
                message_id="msg3",
                company_id="test-company",
                message="Third message",
                subject="Third",
                sender="recruiter3@example.com",
                email_thread_link="https://mail.example.com/thread3",
                thread_id="thread3",
                date=datetime.datetime(
                    2023, 1, 3, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
        ]

        # Save all messages
        for message in messages:
            repo.create_recruiter_message(message)

        # Retrieve the company
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None

        # Test that messages property returns all messages in date order (newest first)
        company_messages = retrieved_company.messages
        assert isinstance(company_messages, list)
        assert len(company_messages) == 3

        # Verify order (newest first due to ORDER BY date DESC)
        assert company_messages[0].message_id == "msg3"
        assert company_messages[0].subject == "Third"
        assert company_messages[1].message_id == "msg2"
        assert company_messages[1].subject == "Second"
        assert company_messages[2].message_id == "msg1"
        assert company_messages[2].subject == "First"

    def test_get_recruiter_messages_method(self, clean_test_db):
        """Test the get_recruiter_messages repository method directly."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create multiple messages
        messages = [
            RecruiterMessage(
                message_id="msg1",
                company_id="test-company",
                message="Message 1",
                subject="Subject 1",
                sender="sender1@example.com",
                email_thread_link="https://mail.example.com/thread1",
                thread_id="thread1",
                date=datetime.datetime(
                    2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
            RecruiterMessage(
                message_id="msg2",
                company_id="test-company",
                message="Message 2",
                subject="Subject 2",
                sender="sender2@example.com",
                email_thread_link="https://mail.example.com/thread2",
                thread_id="thread2",
                date=datetime.datetime(
                    2023, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
        ]

        # Save messages
        for message in messages:
            repo.create_recruiter_message(message)

        # Test the repository method directly
        retrieved_messages = repo.get_recruiter_messages("test-company")
        assert isinstance(retrieved_messages, list)
        assert len(retrieved_messages) == 2

        # Verify messages are returned in date order (newest first)
        assert retrieved_messages[0].message_id == "msg2"
        assert retrieved_messages[1].message_id == "msg1"

    def test_get_recruiter_messages_nonexistent_company(self, clean_test_db):
        """Test that get_recruiter_messages returns empty list for nonexistent company."""
        repo = clean_test_db

        # Test with nonexistent company
        messages = repo.get_recruiter_messages("nonexistent-company")
        assert isinstance(messages, list)
        assert len(messages) == 0

    def test_messages_property_with_messages_without_dates(self, clean_test_db):
        """Test that messages property handles messages without dates correctly."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create a message without a date
        message = RecruiterMessage(
            message_id="msg1",
            company_id="test-company",
            message="Message without date",
            subject="No Date",
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread1",
            thread_id="thread1",
            date=None,
        )
        repo.create_recruiter_message(message)

        # Retrieve the company
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None

        # Test that messages property returns the message
        messages = retrieved_company.messages
        assert isinstance(messages, list)
        assert len(messages) == 1
        assert messages[0].message_id == "msg1"
        assert messages[0].date is None

    def test_legacy_single_message_gets_most_recent(self, clean_test_db):
        """Test that the legacy single message functionality gets the most recent message by date."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create multiple recruiter messages with different dates
        messages = [
            RecruiterMessage(
                message_id="msg1",
                company_id="test-company",
                message="First message",
                subject="First",
                sender="recruiter1@example.com",
                email_thread_link="https://mail.example.com/thread1",
                thread_id="thread1",
                date=datetime.datetime(
                    2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
            RecruiterMessage(
                message_id="msg2",
                company_id="test-company",
                message="Second message",
                subject="Second",
                sender="recruiter2@example.com",
                email_thread_link="https://mail.example.com/thread2",
                thread_id="thread2",
                date=datetime.datetime(
                    2023, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
            RecruiterMessage(
                message_id="msg3",
                company_id="test-company",
                message="Third message",
                subject="Third",
                sender="recruiter3@example.com",
                email_thread_link="https://mail.example.com/thread3",
                thread_id="thread3",
                date=datetime.datetime(
                    2023, 1, 3, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
        ]

        # Save all messages
        for message in messages:
            repo.create_recruiter_message(message)

        # Test the legacy single message method directly
        single_message = repo.get_recruiter_message("test-company")
        assert single_message is not None
        assert single_message.message_id == "msg3"  # Should be the most recent
        assert single_message.subject == "Third"

        # Test that the legacy recruiter_message property on Company also gets the most recent
        retrieved_company = repo.get("test-company")
        assert retrieved_company is not None
        assert retrieved_company.recruiter_message is not None
        assert retrieved_company.recruiter_message.message_id == "msg3"
        assert retrieved_company.recruiter_message.subject == "Third"

        # Verify that the first message in the messages list matches the legacy single message
        all_messages = retrieved_company.messages
        assert len(all_messages) == 3
        assert (
            all_messages[0].message_id == retrieved_company.recruiter_message.message_id
        )
        assert all_messages[0].subject == retrieved_company.recruiter_message.subject

    def test_recruiter_message_deduplication(self, clean_test_db):
        """Test that duplicate recruiter messages are properly deduplicated by message_id."""
        repo = clean_test_db

        # Create a company
        company = Company(
            company_id="test-company",
            name="TestCompany",
            details=CompaniesSheetRow(name="TestCompany"),
        )
        repo.create(company)

        # Create an initial recruiter message
        original_message = RecruiterMessage(
            message_id="duplicate-test-123",
            company_id="test-company",
            message="Original message content",
            subject="Original Subject",
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread123",
            thread_id="thread123",
            date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )
        repo.create_recruiter_message(original_message)

        # Verify the message was created
        messages = repo.get_recruiter_messages("test-company")
        assert len(messages) == 1
        assert messages[0].message_id == "duplicate-test-123"
        assert messages[0].subject == "Original Subject"
        assert messages[0].message == "Original message content"

        # Now create a "duplicate" message with the same message_id but different content
        # This simulates what would happen if the same Gmail message was processed twice
        duplicate_message = RecruiterMessage(
            message_id="duplicate-test-123",  # Same message_id
            company_id="test-company",
            message="Updated message content",  # Different content
            subject="Updated Subject",  # Different subject
            sender="recruiter@example.com",
            email_thread_link="https://mail.example.com/thread123",
            thread_id="thread123",
            date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )
        repo.create_recruiter_message(duplicate_message)

        # Verify that we still have only one message (no duplicate was created)
        messages = repo.get_recruiter_messages("test-company")
        assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"

        # Verify that the message was updated with the new content (upsert behavior)
        updated_message = messages[0]
        assert updated_message.message_id == "duplicate-test-123"
        assert updated_message.subject == "Updated Subject"  # Should be updated
        assert updated_message.message == "Updated message content"  # Should be updated

        # Test the same behavior when creating a company with a duplicate recruiter message
        duplicate_company = Company(
            company_id="another-company",
            name="AnotherCompany",
            details=CompaniesSheetRow(name="AnotherCompany"),
            recruiter_message=RecruiterMessage(
                message_id="duplicate-test-123",  # Same message_id as before
                company_id="another-company",
                message="Yet another message content",
                subject="Yet Another Subject",
                sender="recruiter@example.com",
                email_thread_link="https://mail.example.com/thread123",
                thread_id="thread123",
                date=datetime.datetime(
                    2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
        )
        repo.create(duplicate_company)

        # Verify that we still have only one message across all companies
        all_messages_company1 = repo.get_recruiter_messages("test-company")
        all_messages_company2 = repo.get_recruiter_messages("another-company")

        # The message should now be associated with the company that was created last
        # due to the upsert behavior updating the company_id
        assert (
            len(all_messages_company1) == 0
        )  # Original company no longer has the message
        assert len(all_messages_company2) == 1  # New company has the message

        final_message = all_messages_company2[0]
        assert final_message.message_id == "duplicate-test-123"
        assert final_message.company_id == "another-company"  # Should be updated
        assert final_message.subject == "Yet Another Subject"  # Should be updated
        assert final_message.message == "Yet another message content"  # Should be updated

    def test_get_recruiter_message_by_id_success(self, clean_test_db):
        """Test getting a recruiter message by its message_id."""
        repo = clean_test_db

        # Create a company with a message
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
        )

        # Create a message for this company
        message = RecruiterMessage(
            message_id="test-message-123",
            company_id="test-company",
            subject="Test message",
            message="Test recruiter message",
            thread_id="thread1",
        )

        # Save company and message
        repo.create(company)
        repo.create_recruiter_message(message)

        # Get the message by ID
        retrieved_message = repo.get_recruiter_message_by_id("test-message-123")

        # Verify the message was retrieved correctly
        assert retrieved_message is not None
        assert retrieved_message.message_id == "test-message-123"
        assert retrieved_message.company_id == "test-company"
        assert retrieved_message.subject == "Test message"
        assert retrieved_message.message == "Test recruiter message"

    def test_get_recruiter_message_by_id_not_found(self, clean_test_db):
        """Test getting a recruiter message by non-existent message_id."""
        repo = clean_test_db

        # Try to get a non-existent message
        retrieved_message = repo.get_recruiter_message_by_id("non-existent-message")

        # Verify no message was found
        assert retrieved_message is None

    def test_get_recruiter_message_by_id_multiple_companies(self, clean_test_db):
        """Test getting a message by ID when multiple companies have messages."""
        repo = clean_test_db

        # Create two companies with messages
        company1 = Company(
            company_id="test-company-1",
            name="Test Company 1",
            details=CompaniesSheetRow(name="Test Company 1"),
        )
        company2 = Company(
            company_id="test-company-2",
            name="Test Company 2",
            details=CompaniesSheetRow(name="Test Company 2"),
        )

        # Create messages for both companies
        message1 = RecruiterMessage(
            message_id="message-1",
            company_id="test-company-1",
            subject="Message 1",
            message="First recruiter message",
            thread_id="thread1",
        )
        message2 = RecruiterMessage(
            message_id="message-2",
            company_id="test-company-2",
            subject="Message 2",
            message="Second recruiter message",
            thread_id="thread2",
        )

        # Save companies and messages
        repo.create(company1)
        repo.create(company2)
        repo.create_recruiter_message(message1)
        repo.create_recruiter_message(message2)

        # Get message from company 1
        retrieved_message1 = repo.get_recruiter_message_by_id("message-1")
        assert retrieved_message1 is not None
        assert retrieved_message1.message_id == "message-1"
        assert retrieved_message1.company_id == "test-company-1"

        # Get message from company 2
        retrieved_message2 = repo.get_recruiter_message_by_id("message-2")
        assert retrieved_message2 is not None
        assert retrieved_message2.message_id == "message-2"
        assert retrieved_message2.company_id == "test-company-2"

        # Verify we can't get the wrong message
        wrong_message = repo.get_recruiter_message_by_id("message-1")
        assert wrong_message is not None

    def test_get_recruiter_message_by_id_includes_reply_sent_at(self, clean_test_db):
        """Test that get_recruiter_message_by_id correctly includes reply_sent_at field."""
        repo = clean_test_db

        # Create a company with a message
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
        )

        # Create a message with reply_sent_at set
        message = RecruiterMessage(
            message_id="test-message-with-reply",
            company_id="test-company",
            subject="Test message",
            message="Test recruiter message",
            thread_id="thread1",
            reply_sent_at=datetime.datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc
            ),
        )

        # Save company and message
        repo.create(company)
        repo.create_recruiter_message(message)

        # Get the message by ID
        retrieved_message = repo.get_recruiter_message_by_id("test-message-with-reply")

        # Verify the message was retrieved correctly with reply_sent_at
        assert retrieved_message is not None
        assert retrieved_message.message_id == "test-message-with-reply"
        assert retrieved_message.reply_sent_at is not None
        assert retrieved_message.reply_sent_at == datetime.datetime(
            2025, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc
        )

    def test_get_recruiter_message_by_id_handles_null_reply_sent_at(self, clean_test_db):
        """Test that get_recruiter_message_by_id correctly handles null reply_sent_at."""
        repo = clean_test_db

        # Create a company with a message
        company = Company(
            company_id="test-company",
            name="Test Company",
            details=CompaniesSheetRow(name="Test Company"),
        )

        # Create a message without reply_sent_at
        message = RecruiterMessage(
            message_id="test-message-no-reply",
            company_id="test-company",
            subject="Test message",
            message="Test recruiter message",
            thread_id="thread1",
            reply_sent_at=None,
        )

        # Save company and message
        repo.create(company)
        repo.create_recruiter_message(message)

        # Get the message by ID
        retrieved_message = repo.get_recruiter_message_by_id("test-message-no-reply")

        # Verify the message was retrieved correctly with null reply_sent_at
        assert retrieved_message is not None
        assert retrieved_message.message_id == "test-message-no-reply"
        assert retrieved_message.reply_sent_at is None


class TestIsPlaceholder:

    def test_is_placeholder_company_from_variations(self):
        """Test detection of 'Company from' placeholder patterns."""
        assert is_placeholder("Company from email")
        assert is_placeholder("company from somewhere")
        assert is_placeholder("Company from LinkedIn")
        assert is_placeholder("Company from recruiter message")

    def test_is_placeholder_unknown_variations(self):
        """Test detection of '<UNKNOWN' placeholder patterns."""
        assert is_placeholder("<UNKNOWN>")
        assert is_placeholder("<unknown company>")
        assert is_placeholder("<UNKNOWN - no info>")
        assert is_placeholder("<unknown>")

    def test_is_placeholder_case_insensitive(self):
        """Test placeholder detection is case insensitive."""
        assert is_placeholder("COMPANY FROM EMAIL")
        assert is_placeholder("<UNKNOWN>")
        assert is_placeholder("Unknown")
        assert is_placeholder("PLACEHOLDER")

    def test_is_placeholder_whitespace_handling(self):
        """Test placeholder detection handles leading/trailing whitespace."""
        assert is_placeholder("  Company from email  ")
        assert is_placeholder("\t<unknown>\n")
        assert is_placeholder("  unknown  ")
        assert is_placeholder("")

    def test_is_placeholder_none_and_empty(self):
        """Test placeholder detection handles None and empty values."""
        assert is_placeholder(None)
        assert is_placeholder("")
        assert is_placeholder("   ")

    def test_is_placeholder_non_placeholder_names(self):
        """Test that legitimate company names are not flagged as placeholders."""
        assert not is_placeholder("Google")
        assert not is_placeholder("Microsoft Corporation")
        assert not is_placeholder("Acme Inc")
        assert not is_placeholder("Tech Startup 2024")
        assert not is_placeholder("Some Company LLC")

    def test_is_placeholder_exact_matches(self):
        """Test exact placeholder matches."""
        assert is_placeholder("unknown")
        assert is_placeholder("placeholder")
        assert not is_placeholder("unknown company")  # Not exact match
        assert not is_placeholder("placeholder inc")  # Not exact match
