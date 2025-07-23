from unittest.mock import patch

import pytest
from pyramid.testing import DummyRequest  # type: ignore[import-untyped]

import server.app
import tasks
from models import CompaniesSheetRow, Company, CompanyStatus, RecruiterMessage


@pytest.fixture
def mock_task_manager():
    with patch("tasks.task_manager") as mock:
        yield mock.return_value


@pytest.fixture
def mock_company_repo():
    with patch("models.company_repository") as mock:
        yield mock.return_value


@pytest.fixture
def test_company():
    """Fixture to create a test company."""
    company_name = "Test Corp"
    company_id = "test-corp"
    return Company(
        company_id=company_id,
        name=company_name,
        details=CompaniesSheetRow(name=company_name),
        status=CompanyStatus(),
    )


def test_research_by_url(mock_task_manager):
    """Test starting research with a URL."""
    request = DummyRequest(json_body={"url": "https://example.com"})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.research_by_url_or_name(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.COMPANY_RESEARCH,
        {"company_url": "https://example.com"},
    )


def test_research_by_name(mock_task_manager):
    """Test starting research with a name."""
    request = DummyRequest(json_body={"name": "Test Corp"})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.research_by_url_or_name(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.COMPANY_RESEARCH,
        {"company_name": "Test Corp"},
    )


def test_research_by_url_and_name(mock_task_manager):
    """Test starting research with both URL and name."""
    request = DummyRequest(json_body={"url": "https://example.com", "name": "Test Corp"})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.research_by_url_or_name(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.COMPANY_RESEARCH,
        {"company_url": "https://example.com", "company_name": "Test Corp"},
    )


def test_research_missing_params():
    """Test starting research with no parameters."""
    request = DummyRequest(json_body={})

    response = server.app.research_by_url_or_name(request)

    assert response["error"] == "Either company URL or name must be provided"
    assert request.response.status == "400 Bad Request"


def test_research_error(mock_task_manager):
    """Test error handling when starting research."""
    request = DummyRequest(json_body={"url": "https://example.com"})
    mock_task_manager.create_task.side_effect = Exception("Task creation failed")

    response = server.app.research_by_url_or_name(request)

    assert response["error"] == "Task creation failed"


def test_research_by_url_or_name_no_params():
    """Test research with missing parameters."""
    request = DummyRequest(json_body={})

    response = server.app.research_by_url_or_name(request)

    assert response["error"] == "Either company URL or name must be provided"


def test_import_companies_from_spreadsheet(mock_task_manager):
    """Test importing companies from spreadsheet."""
    request = DummyRequest(json_body={})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.import_companies_from_spreadsheet(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.IMPORT_COMPANIES_FROM_SPREADSHEET,
        {},
    )


def test_scan_recruiter_emails_default_behavior(mock_task_manager):
    """Test scan_recruiter_emails with default parameters (should fetch all messages)."""
    request = DummyRequest(json_body={})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.scan_recruiter_emails(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": None, "do_research": False},
    )


def test_scan_recruiter_emails_with_custom_max_messages(mock_task_manager):
    """Test scan_recruiter_emails with custom max_messages parameter."""
    request = DummyRequest(json_body={"max_messages": 50})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.scan_recruiter_emails(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": 50, "do_research": False},
    )


def test_scan_recruiter_emails_with_research_enabled(mock_task_manager):
    """Test scan_recruiter_emails with research enabled."""
    request = DummyRequest(json_body={"do_research": True})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.scan_recruiter_emails(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": None, "do_research": True},
    )


def test_scan_recruiter_emails_with_both_parameters(mock_task_manager):
    """Test scan_recruiter_emails with both max_messages and do_research parameters."""
    request = DummyRequest(json_body={"max_messages": 25, "do_research": True})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.scan_recruiter_emails(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": 25, "do_research": True},
    )


def test_scan_recruiter_emails_with_null_max_messages(mock_task_manager):
    """Test scan_recruiter_emails with explicit null max_messages (should mean unlimited)."""
    request = DummyRequest(json_body={"max_messages": None, "do_research": False})
    mock_task_manager.create_task.return_value = "task-123"

    response = server.app.scan_recruiter_emails(request)

    assert response["task_id"] == "task-123"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.FIND_COMPANIES_FROM_RECRUITER_MESSAGES,
        {"max_messages": None, "do_research": False},
    )


# Add fixture for database tests
import os

from models import CompanyRepository, RecruiterMessage

TEST_DB_PATH = "data/_test_companies_endpoint.db"


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


def test_ignore_and_archive_specific_message(clean_test_db):
    """Test archiving a specific message by message_id"""
    repo = clean_test_db

    # Create a company with multiple messages
    company = Company(
        company_id="test-msg-archive",
        name="Test Message Archive",
        details=CompaniesSheetRow(name="Test Message Archive"),
    )

    # Create two messages for this company
    message1 = RecruiterMessage(
        message_id="msg1",
        company_id="test-msg-archive",
        subject="First message",
        message="First recruiter message",
        thread_id="thread1",
    )
    message2 = RecruiterMessage(
        message_id="msg2",
        company_id="test-msg-archive",
        subject="Second message",
        message="Second recruiter message",
        thread_id="thread2",
    )

    # Save company and messages
    repo.create(company)
    repo.create_recruiter_message(message1)
    repo.create_recruiter_message(message2)

    # Mock the repository in the app
    with patch("models.company_repository", return_value=repo):
        # Archive specific message
        request = DummyRequest(json_body={"message_id": "msg1"})
        request.matchdict = {"company_id": "test-msg-archive"}

        response = server.app.ignore_and_archive(request)

        # Check response
        assert response["message"] == "Message archived successfully"
        assert response["message_id"] == "msg1"
        assert "archived_at" in response

        # Verify the specific message was archived
        messages = repo.get_recruiter_messages("test-msg-archive")
        archived_msg = next(msg for msg in messages if msg.message_id == "msg1")
        unarchived_msg = next(msg for msg in messages if msg.message_id == "msg2")

        assert archived_msg.archived_at is not None
        assert unarchived_msg.archived_at is None

        # Verify company itself is not archived
        updated_company = repo.get("test-msg-archive")
        assert updated_company.status.archived_at is None


def test_ignore_and_archive_without_message_id_still_works(
    clean_test_db, mock_task_manager
):
    """Test that company-level archiving still works when no message_id is provided"""
    repo = clean_test_db

    # Create a company
    company = Company(
        company_id="test-company-archive",
        name="Test Company Archive",
        details=CompaniesSheetRow(name="Test Company Archive"),
    )
    repo.create(company)

    # Mock the repository and task manager
    mock_task_manager.create_task.return_value = "task-123"

    with patch("models.company_repository", return_value=repo):
        # Archive company (no message_id in body)
        request = DummyRequest(json_body={})  # Empty body, no message_id
        request.matchdict = {"company_id": "test-company-archive"}

        response = server.app.ignore_and_archive(request)

        # Check response has task_id (company-level archiving)
        assert "task_id" in response
        assert "archived_at" in response
        assert response["task_id"] == "task-123"

        # Verify company was archived
        updated_company = repo.get("test-company-archive")
        assert updated_company.status.archived_at is not None


def test_ignore_and_archive_message_not_found(clean_test_db):
    """Test error handling when message_id doesn't exist"""
    repo = clean_test_db

    # Create a company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)

    with patch("models.company_repository", return_value=repo):
        # Try to archive non-existent message
        request = DummyRequest(json_body={"message_id": "non-existent"})
        request.matchdict = {"company_id": "test-company"}

        response = server.app.ignore_and_archive(request)

        # Check error response
        assert response["error"] == "Message not found"


def test_archive_message_by_id_success(clean_test_db):
    """Test archiving a specific message using the new /messages/{message_id}/archive endpoint"""
    repo = clean_test_db

    # Create a company with a message
    company = Company(
        company_id="test-msg-archive",
        name="Test Message Archive",
        details=CompaniesSheetRow(name="Test Message Archive"),
    )

    # Create a message for this company
    message = RecruiterMessage(
        message_id="msg1",
        company_id="test-msg-archive",
        subject="Test message",
        message="Test recruiter message",
        thread_id="thread1",
    )

    # Save company and message
    repo.create(company)
    repo.create_recruiter_message(message)

    # Mock the repository in the app
    with patch("models.company_repository", return_value=repo):
        # Archive specific message using new endpoint
        request = DummyRequest()
        request.matchdict = {"message_id": "msg1"}

        response = server.app.archive_message_by_id(request)

        # Check response
        assert response["message"] == "Message archived successfully"
        assert response["message_id"] == "msg1"
        assert "archived_at" in response

        # Verify the message was archived
        messages = repo.get_recruiter_messages("test-msg-archive")
        archived_msg = next(msg for msg in messages if msg.message_id == "msg1")
        assert archived_msg.archived_at is not None

        # Verify company itself is not archived
        updated_company = repo.get("test-msg-archive")
        assert updated_company.status.archived_at is None


def test_archive_message_by_id_not_found(clean_test_db):
    """Test error handling when message_id doesn't exist in new endpoint"""
    repo = clean_test_db

    # Create a company without any messages
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)

    with patch("models.company_repository", return_value=repo):
        # Try to archive non-existent message
        request = DummyRequest()
        request.matchdict = {"message_id": "non-existent"}

        response = server.app.archive_message_by_id(request)

        # Check error response
        assert response["error"] == "Message not found"
        assert request.response.status == "404 Not Found"


def test_archive_message_by_id_multiple_companies(clean_test_db):
    """Test that archiving a message only affects the specific message, not other companies"""
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
        message_id="msg1",
        company_id="test-company-1",
        subject="Message 1",
        message="First recruiter message",
        thread_id="thread1",
    )
    message2 = RecruiterMessage(
        message_id="msg2",
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

    # Mock the repository in the app
    with patch("models.company_repository", return_value=repo):
        # Archive message from company 1
        request = DummyRequest()
        request.matchdict = {"message_id": "msg1"}

        response = server.app.archive_message_by_id(request)

        # Check response
        assert response["message"] == "Message archived successfully"
        assert response["message_id"] == "msg1"

        # Verify only message1 was archived
        messages1 = repo.get_recruiter_messages("test-company-1")
        messages2 = repo.get_recruiter_messages("test-company-2")

        archived_msg1 = next(msg for msg in messages1 if msg.message_id == "msg1")
        unarchived_msg2 = next(msg for msg in messages2 if msg.message_id == "msg2")

        assert archived_msg1.archived_at is not None
        assert unarchived_msg2.archived_at is None
