import datetime
import os
from unittest.mock import patch

import pytest
from pyramid.testing import DummyRequest  # type: ignore[import-untyped]

import server.app
import tasks
from models import CompaniesSheetRow, Company, CompanyStatus, RecruiterMessage
from models import CompanyRepository

TEST_DB_PATH = "data/_test_companies_endpoint.db"


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


# Remove tests for old ignore_and_archive endpoint since it's been removed


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


def test_generate_message_by_id_success(clean_test_db, mock_task_manager):
    """Test successful reply generation for a specific message."""
    repo = clean_test_db
    mock_task_manager.create_task.return_value = "task-123"

    # Create a company with a message
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    message = RecruiterMessage(
        message_id="msg1",
        company_id="test-company",
        subject="Test Message",
        message="Test recruiter message",
        thread_id="thread1",
    )

    # Save company and message
    repo.create(company)
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"message_id": "msg1"}

        response = server.app.generate_message_by_id(request)

        # Check response
        assert response["task_id"] == "task-123"
        assert response["status"] == tasks.TaskStatus.PENDING.value

        # Verify task was created with correct company_id
        mock_task_manager.create_task.assert_called_once_with(
            tasks.TaskType.GENERATE_REPLY,
            {"company_id": "test-company"},
        )


def test_generate_message_by_id_message_not_found(clean_test_db, mock_task_manager):
    """Test error handling when message_id doesn't exist."""
    repo = clean_test_db

    # Create a company without any messages
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"message_id": "non-existent"}

        response = server.app.generate_message_by_id(request)

        # Check error response
        assert response["error"] == "Message not found"
        assert request.response.status == "404 Not Found"

        # Verify no task was created
        mock_task_manager.create_task.assert_not_called()


def test_generate_message_by_id_company_not_found(clean_test_db, mock_task_manager):
    """Test error handling when company associated with message doesn't exist."""
    repo = clean_test_db

    # Create a message with a non-existent company_id
    message = RecruiterMessage(
        message_id="msg1",
        company_id="non-existent-company",
        subject="Test Message",
        message="Test recruiter message",
        thread_id="thread1",
    )
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"message_id": "msg1"}

        response = server.app.generate_message_by_id(request)

        # Check error response
        assert response["error"] == "Company not found for this message"
        assert request.response.status == "404 Not Found"

        # Verify no task was created
        mock_task_manager.create_task.assert_not_called()


def test_generate_message_by_id_missing_message_id(clean_test_db, mock_task_manager):
    """Test error handling when message_id is missing."""
    with patch("models.company_repository", return_value=clean_test_db):
        request = DummyRequest()
        request.matchdict = {"message_id": ""}

        response = server.app.generate_message_by_id(request)

        # Check error response
        assert response["error"] == "Message ID is required"
        assert request.response.status == "400 Bad Request"

        # Verify no task was created
        mock_task_manager.create_task.assert_not_called()


def test_update_message_by_id_success(clean_test_db):
    """Test successful reply message update for a specific message."""
    repo = clean_test_db

    # Create a company with a message
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        reply_message="Old reply",
    )
    message = RecruiterMessage(
        message_id="msg1",
        company_id="test-company",
        subject="Test Message",
        message="Test recruiter message",
        thread_id="thread1",
    )

    # Save company and message
    repo.create(company)
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "New reply message"})
        request.matchdict = {"message_id": "msg1"}

        response = server.app.update_message_by_id(request)

        # Check response contains updated company data
        assert response["reply_message"] == "New reply message"
        assert response["name"] == "Test Company"

        # Verify the company was updated in the database
        updated_company = repo.get("test-company")
        assert updated_company.reply_message == "New reply message"


def test_update_message_by_id_message_not_found(clean_test_db):
    """Test error handling when message_id doesn't exist."""
    repo = clean_test_db

    # Create a company without any messages
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "New reply"})
        request.matchdict = {"message_id": "non-existent"}

        response = server.app.update_message_by_id(request)

        # Check error response
        assert response["error"] == "Message not found"
        assert request.response.status == "404 Not Found"


def test_update_message_by_id_company_not_found(clean_test_db):
    """Test error handling when company associated with message doesn't exist."""
    repo = clean_test_db

    # Create a message with a non-existent company_id
    message = RecruiterMessage(
        message_id="msg1",
        company_id="non-existent-company",
        subject="Test Message",
        message="Test recruiter message",
        thread_id="thread1",
    )
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "New reply"})
        request.matchdict = {"message_id": "msg1"}

        response = server.app.update_message_by_id(request)

        # Check error response
        assert response["error"] == "Company not found for this message"
        assert request.response.status == "404 Not Found"


def test_update_message_by_id_missing_message_id(clean_test_db):
    """Test error handling when message_id is missing."""
    with patch("models.company_repository", return_value=clean_test_db):
        request = DummyRequest(json_body={"message": "New reply"})
        request.matchdict = {"message_id": ""}

        response = server.app.update_message_by_id(request)

        # Check error response
        assert response["error"] == "Message ID is required"
        assert request.response.status == "400 Bad Request"


def test_update_message_by_id_missing_message_body(clean_test_db):
    """Test error handling when message body is missing."""
    repo = clean_test_db

    # Create a company with a message
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    message = RecruiterMessage(
        message_id="msg1",
        company_id="test-company",
        subject="Test Message",
        message="Test recruiter message",
        thread_id="thread1",
    )

    # Save company and message
    repo.create(company)
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={})
        request.matchdict = {"message_id": "msg1"}

        response = server.app.update_message_by_id(request)

        # Check error response
        assert response["error"] == "Message is required"
        assert request.response.status == "400 Bad Request"


def test_update_message_by_id_invalid_json(clean_test_db):
    """Test error handling when JSON is invalid."""
    with patch("models.company_repository", return_value=clean_test_db):
        request = DummyRequest()
        request.json_body = None  # This will cause JSONDecodeError
        request.matchdict = {"message_id": "msg1"}

        response = server.app.update_message_by_id(request)

        # Check error response
        assert response["error"] == "Invalid JSON"
        assert request.response.status == "400 Bad Request"


def test_get_messages_endpoint(clean_test_db):
    """Test the GET /api/messages endpoint returns all messages with company info."""
    # Create test companies with messages
    repo = clean_test_db

    # Company 1 with a message
    company1 = Company(
        company_id="test-corp-1",
        name="Test Corp 1",
        details=CompaniesSheetRow(name="Test Corp 1"),
        status=CompanyStatus(),
    )
    repo.create(company1)

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

    # Company 2 with a message
    company2 = Company(
        company_id="test-corp-2",
        name="Test Corp 2",
        details=CompaniesSheetRow(name="Test Corp 2"),
        status=CompanyStatus(),
    )
    repo.create(company2)

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

    # Test the endpoint
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    # Verify response structure
    assert isinstance(response, list)
    assert len(response) == 2

    # Verify first message
    msg1_data = next(msg for msg in response if msg["message_id"] == "msg-1")
    assert msg1_data["message_id"] == "msg-1"
    assert msg1_data["company_id"] == "test-corp-1"
    assert msg1_data["subject"] == "Test Subject 1"
    assert msg1_data["sender"] == "recruiter1@test.com"
    assert msg1_data["company_name"] == "Test Corp 1"
    assert "date" in msg1_data
    assert "archived_at" in msg1_data

    # Verify second message
    msg2_data = next(msg for msg in response if msg["message_id"] == "msg-2")
    assert msg2_data["message_id"] == "msg-2"
    assert msg2_data["company_id"] == "test-corp-2"
    assert msg2_data["subject"] == "Test Subject 2"
    assert msg2_data["sender"] == "recruiter2@test.com"
    assert msg2_data["company_name"] == "Test Corp 2"
    assert "date" in msg2_data
    assert "archived_at" in msg2_data


def test_get_messages_endpoint_empty(clean_test_db):
    """Test the GET /api/messages endpoint returns empty list when no messages exist."""
    repo = clean_test_db
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

        assert isinstance(response, list)
        assert len(response) == 0
