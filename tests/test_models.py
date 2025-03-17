import datetime
import os
import pytest
import shutil
from typing import Optional

from models import (
    CompanyRepository,
    Company,
    CompaniesSheetRow,
    RecruiterMessage,
    company_repository,
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
        assert created_company.name == "TestCompany"
        assert created_company.details.name == "TestCompany"
        assert created_company.details.type == "Private"
        assert created_company.details.url == "https://testcompany.example.com"
        assert created_company.reply_message == "Test reply"
        
        # Retrieve it from the database
        retrieved_company = repo.get("TestCompany")
        
        # Verify it matches what we created
        assert retrieved_company is not None
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
        retrieved_company = repo.get("TestCompany")
        assert retrieved_company is not None
        assert retrieved_company.details.type == "Public"
        assert retrieved_company.reply_message == "Updated reply"
    
    def test_delete_company(self, clean_test_db):
        """Test deleting a company."""
        repo = clean_test_db
        
        # Create a test company
        company = Company(
            name="TestCompany",
            details=CompaniesSheetRow(
                name="TestCompany",
            ),
        )
        
        # Save it to the database
        repo.create(company)
        
        # Verify it exists
        assert repo.get("TestCompany") is not None
        
        # Delete it
        repo.delete("TestCompany")
        
        # Verify it no longer exists
        assert repo.get("TestCompany") is None
    
    def test_get_all_companies(self, clean_test_db):
        """Test retrieving all companies."""
        repo = clean_test_db
        
        # Create multiple test companies
        companies = [
            Company(
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
        company_names = {company.name for company in all_companies}
        assert company_names == {"TestCompany0", "TestCompany1", "TestCompany2"}
    
    def test_company_with_recruiter_message(self, clean_test_db):
        """Test creating and retrieving a company with a recruiter message."""
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
        assert created_company.name == "TestCompany"
        
        # Retrieve the company with the recruiter message
        retrieved_company = repo.get("TestCompany")
        
        # Verify the recruiter message was saved and retrieved correctly
        assert retrieved_company is not None
        assert retrieved_company.recruiter_message is not None
        assert retrieved_company.recruiter_message.message_id == "test123"
        assert retrieved_company.recruiter_message.message == "Hello, we have a job opportunity for you."
        assert retrieved_company.recruiter_message.subject == "Job Opportunity"
        assert retrieved_company.recruiter_message.sender == "recruiter@example.com"
        assert retrieved_company.recruiter_message.email_thread_link == "https://mail.example.com/thread123"
        assert retrieved_company.recruiter_message.thread_id == "thread123"
        assert retrieved_company.recruiter_message.date == datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    
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
        retrieved_company = repo.get("TestCompany")
        
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
    
    def test_from_list(self):
        """Test creating a CompaniesSheetRow from a list of strings."""
        # Create a list with values for the first few fields
        row_data = ["TestCompany", "Private", "100M", "Series B", "yes", "https://example.com"]
        
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
        assert company.recruiter_message.message == "Updated message"
        
        # Test with no recruiter message
        company = Company(
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
