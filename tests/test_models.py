import datetime
import json
import os
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
        updated_company = repo.update(created_company)

        # Retrieve the company again
        retrieved_company = repo.get("test-company")

        # Verify the company and recruiter message were updated correctly
        assert retrieved_company is not None
        assert retrieved_company.details.type == "Public"
        assert retrieved_company.recruiter_message is not None
        assert retrieved_company.recruiter_message.subject == "Updated Job Opportunity"
        assert retrieved_company.recruiter_message.message == "Updated message content"
        assert retrieved_company.recruiter_message.message_id == "test123"


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
        row: CompaniesSheetRow = CompaniesSheetRow.from_list(row_data)

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
    now = datetime.datetime.now(datetime.timezone.utc)

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
