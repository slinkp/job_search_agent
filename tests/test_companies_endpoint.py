import datetime
from unittest.mock import patch

import pytest
from pyramid.testing import DummyRequest  # type: ignore[import-untyped]

import server.app
import tasks
from models import CompaniesSheetRow, Company, CompanyStatus, RecruiterMessage

from .utils import make_clean_test_db_fixture

TEST_DB_PATH = "data/_test_companies_endpoint.db"


clean_test_db = make_clean_test_db_fixture(TEST_DB_PATH)


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
        name="Company from Blech <blech@blech.com>",
        details=CompaniesSheetRow(name="Company from Ugh"),
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
        assert response["name"] == "Company from Blech <blech@blech.com>"

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


def test_get_messages_endpoint_includes_reply_fields(clean_test_db):
    """Test the GET /api/messages endpoint includes reply_message and reply_status fields."""
    repo = clean_test_db

    # Create test company with reply message
    company = Company(
        company_id="test-corp",
        name="Test Corp",
        details=CompaniesSheetRow(name="Test Corp"),
        status=CompanyStatus(),
        reply_message="Generated reply for Test Corp",
    )
    repo.create(company)

    # Create message with reply_sent_at set (sent message)
    sent_message = RecruiterMessage(
        message_id="sent-msg",
        company_id="test-corp",
        subject="Sent Message",
        sender="recruiter@test.com",
        date=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="Test message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread1",
        thread_id="thread1",
        reply_sent_at=datetime.datetime(
            2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
        ),
    )
    repo.create_recruiter_message(sent_message)

    # Create message without reply_sent_at (generated but not sent)
    generated_message = RecruiterMessage(
        message_id="generated-msg",
        company_id="test-corp",
        subject="Generated Message",
        sender="recruiter@test.com",
        date=datetime.datetime(2024, 1, 3, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="Test message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread2",
        thread_id="thread2",
    )
    repo.create_recruiter_message(generated_message)

    # Create company without reply message
    company_no_reply = Company(
        company_id="test-corp-no-reply",
        name="Test Corp No Reply",
        details=CompaniesSheetRow(name="Test Corp No Reply"),
        status=CompanyStatus(),
    )
    repo.create(company_no_reply)

    # Create message for company without reply
    no_reply_message = RecruiterMessage(
        message_id="no-reply-msg",
        company_id="test-corp-no-reply",
        subject="No Reply Message",
        sender="recruiter@test.com",
        date=datetime.datetime(2024, 1, 4, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="Test message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread3",
        thread_id="thread3",
    )
    repo.create_recruiter_message(no_reply_message)

    # Test the endpoint
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    # Verify response structure
    assert isinstance(response, list)
    assert len(response) == 3

    # Verify sent message (should have reply_status="sent")
    sent_msg_data = next(msg for msg in response if msg["message_id"] == "sent-msg")
    assert sent_msg_data["reply_message"] == "Generated reply for Test Corp"
    assert sent_msg_data["reply_status"] == "sent"

    # Verify generated message (should have reply_status="generated")
    generated_msg_data = next(
        msg for msg in response if msg["message_id"] == "generated-msg"
    )
    assert generated_msg_data["reply_message"] == "Generated reply for Test Corp"
    assert generated_msg_data["reply_status"] == "generated"

    # Verify no reply message (should have reply_status="none")
    no_reply_msg_data = next(
        msg for msg in response if msg["message_id"] == "no-reply-msg"
    )
    assert no_reply_msg_data["reply_message"] == ""
    assert no_reply_msg_data["reply_status"] == "none"


def test_get_companies_sort_by_activity(clean_test_db):
    """Test sorting companies by activity via API (sort=activity)."""
    repo = clean_test_db

    # Create companies
    company_old = Company(
        company_id="company-old",
        name="Old Co",
        details=CompaniesSheetRow(name="Old Co"),
        status=CompanyStatus(),
    )
    company_new = Company(
        company_id="company-new",
        name="New Co",
        details=CompaniesSheetRow(name="New Co"),
        status=CompanyStatus(),
    )
    company_none = Company(
        company_id="company-none",
        name="No Activity Co",
        details=CompaniesSheetRow(name="No Activity Co"),
        status=CompanyStatus(),
    )
    repo.create(company_old)
    repo.create(company_new)
    repo.create(company_none)

    # Set activity: old earlier than new
    older = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    newer = datetime.datetime(2024, 2, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    repo.update_activity("company-old", older, "message received")
    repo.update_activity("company-new", newer, "reply sent")

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.params = {"include_all": "true", "sort": "activity"}
        response = server.app.get_companies(request)

    names = [c["name"] for c in response]
    # Expect New Co (newer activity), then Old Co, then No Activity
    assert names[0] == "New Co"
    assert names[1] == "Old Co"
    assert names[-1] == "No Activity Co"


def test_update_message_by_id_updates_activity_fields(clean_test_db):
    """Updating a reply should set activity_at and last_activity to 'reply edited'."""
    repo = clean_test_db

    company = Company(
        company_id="activity-edit",
        name="Activity Edit Co",
        details=CompaniesSheetRow(name="Activity Edit Co"),
        status=CompanyStatus(),
        reply_message="Old",
    )
    message = RecruiterMessage(
        message_id="msg-edit",
        company_id="activity-edit",
        subject="Subj",
        message="Body",
        thread_id="t1",
    )
    repo.create(company)
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "New body"})
        request.matchdict = {"message_id": "msg-edit"}
        response = server.app.update_message_by_id(request)

    # Response should include activity fields
    assert "activity_at" in response
    assert response.get("last_activity") == "reply edited"

    # DB should be updated as well
    updated = repo.get("activity-edit")
    assert updated is not None
    assert updated.activity_at is not None
    assert updated.last_activity == "reply edited"


def test_send_and_archive_message_updates_activity_fields(
    mock_task_manager, mock_company_repo, test_company
):
    """Sending and archiving should set activity to 'reply sent'."""
    test_message = RecruiterMessage(
        message_id="msg-send-arch",
        company_id=test_company.company_id,
        subject="Subj",
        message="Body",
        thread_id="t1",
        date=datetime.datetime.now(datetime.timezone.utc),
    )
    test_company.reply_message = "Hello"

    mock_company_repo.get_recruiter_message_by_id.return_value = test_message
    mock_company_repo.get.return_value = test_company
    mock_task_manager.create_task.return_value = "tid"

    request = DummyRequest()
    request.matchdict = {"message_id": "msg-send-arch"}
    resp = server.app.send_and_archive_message(request)

    assert "sent_at" in resp and "archived_at" in resp
    # Ensure activity update was attempted on repo
    mock_company_repo.update_activity.assert_called()


def test_archive_message_by_id_updates_activity_fields(clean_test_db):
    """Archiving a message should set activity to 'message archived'."""
    repo = clean_test_db

    company = Company(
        company_id="activity-archive",
        name="Activity Archive Co",
        details=CompaniesSheetRow(name="Activity Archive Co"),
        status=CompanyStatus(),
    )
    message = RecruiterMessage(
        message_id="msg-arch",
        company_id="activity-archive",
        subject="Subj",
        message="Body",
        thread_id="t1",
    )
    repo.create(company)
    repo.create_recruiter_message(message)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"message_id": "msg-arch"}
        _ = server.app.archive_message_by_id(request)

    # Verify DB activity fields
    updated = repo.get("activity-archive")
    assert updated is not None
    assert updated.activity_at is not None
    assert updated.last_activity == "message archived"


def test_get_companies_filters_replied_and_archived(clean_test_db):
    """Test that replied and archived companies are filtered out via the API endpoint."""
    repo = clean_test_db

    # Create test companies
    replied_company = Company(
        company_id="replied-company",
        name="Replied Company",
        details=CompaniesSheetRow(name="Replied Company"),
        status=CompanyStatus(),
    )
    replied_company.status.reply_sent_at = datetime.datetime.now(datetime.timezone.utc)

    archived_company = Company(
        company_id="archived-company",
        name="Archived Company",
        details=CompaniesSheetRow(name="Archived Company"),
        status=CompanyStatus(),
    )
    archived_company.status.archived_at = datetime.datetime.now(datetime.timezone.utc)

    normal_company = Company(
        company_id="normal-company",
        name="Normal Company",
        details=CompaniesSheetRow(name="Normal Company"),
        status=CompanyStatus(),
    )

    # Save companies
    repo.create(replied_company)
    repo.create(archived_company)
    repo.create(normal_company)

    with patch("models.company_repository", return_value=repo):
        # Test default filtering (no include_all parameter)
        request = DummyRequest()
        request.params = {}
        response = server.app.get_companies(request)

        company_names = [c["name"] for c in response]
        assert "Normal Company" in company_names
        assert "Replied Company" not in company_names
        assert "Archived Company" not in company_names

        # Test with include_all=true (should show all companies)
        request = DummyRequest()
        request.params = {"include_all": "true"}
        response = server.app.get_companies(request)

        company_names = [c["name"] for c in response]
        # When include_all=true, we expect to see all companies
        all_expected = ["Normal Company", "Replied Company", "Archived Company"]
        for name in all_expected:
            assert (
                name in company_names
            ), f"Expected {name} to be in response when include_all=true"


def test_send_and_archive_message_success(
    mock_task_manager, mock_company_repo, test_company
):
    """Test successful send and archive for a specific message."""
    # Create a test message
    test_message = RecruiterMessage(
        message_id="test-message-123",
        company_id=test_company.company_id,
        subject="Test Subject",
        sender="test@example.com",
        message="Test message content",
        thread_id="thread-123",
        date=datetime.datetime.now(datetime.timezone.utc),
    )

    # Set up the company with a reply message
    test_company.reply_message = "Test reply message"

    # Mock the repository methods
    mock_company_repo.get_recruiter_message_by_id.return_value = test_message
    mock_company_repo.get.return_value = test_company
    mock_task_manager.create_task.return_value = "task-456"

    # Create the request
    request = DummyRequest()
    request.matchdict = {"message_id": "test-message-123"}

    # Call the endpoint
    response = server.app.send_and_archive_message(request)

    # Verify the response
    assert response["task_id"] == "task-456"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    assert "sent_at" in response
    assert "archived_at" in response
    assert response["message_id"] == "test-message-123"

    # Verify the task was created with correct arguments
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.SEND_AND_ARCHIVE,
        {"company_id": test_company.company_id},
    )

    # Verify the company was updated with sent/archived timestamps
    assert test_company.status.reply_sent_at is not None
    assert test_company.status.archived_at is not None
    mock_company_repo.update.assert_called_once_with(test_company)

    # Verify the message was updated with reply_sent_at and archived_at
    assert test_message.reply_sent_at is not None
    assert test_message.archived_at is not None
    mock_company_repo.create_recruiter_message.assert_called_once_with(test_message)


def test_send_and_archive_message_not_found(mock_company_repo):
    """Test send and archive when message is not found."""
    mock_company_repo.get_recruiter_message_by_id.return_value = None

    request = DummyRequest()
    request.matchdict = {"message_id": "nonexistent-message"}

    response = server.app.send_and_archive_message(request)

    assert response["error"] == "Message not found"
    assert request.response.status == "404 Not Found"


def test_send_and_archive_message_company_not_found(mock_company_repo):
    """Test send and archive when company is not found."""
    test_message = RecruiterMessage(
        message_id="test-message-123",
        company_id="nonexistent-company",
        subject="Test Subject",
        sender="test@example.com",
        message="Test message content",
        thread_id="thread-123",
        date=datetime.datetime.now(datetime.timezone.utc),
    )

    mock_company_repo.get_recruiter_message_by_id.return_value = test_message
    mock_company_repo.get.return_value = None

    request = DummyRequest()
    request.matchdict = {"message_id": "test-message-123"}

    response = server.app.send_and_archive_message(request)

    assert response["error"] == "Company not found for this message"
    assert request.response.status == "404 Not Found"


def test_send_and_archive_message_no_reply(mock_company_repo, test_company):
    """Test send and archive when company has no reply message."""
    test_message = RecruiterMessage(
        message_id="test-message-123",
        company_id=test_company.company_id,
        subject="Test Subject",
        sender="test@example.com",
        message="Test message content",
        thread_id="thread-123",
        date=datetime.datetime.now(datetime.timezone.utc),
    )

    # Company has no reply message
    test_company.reply_message = None

    mock_company_repo.get_recruiter_message_by_id.return_value = test_message
    mock_company_repo.get.return_value = test_company

    request = DummyRequest()
    request.matchdict = {"message_id": "test-message-123"}

    response = server.app.send_and_archive_message(request)

    assert response["error"] == "No reply message to send"
    assert request.response.status == "400 Bad Request"


def test_send_and_archive_message_missing_message_id():
    """Test send and archive with missing message_id."""
    request = DummyRequest()
    request.matchdict = {}

    response = server.app.send_and_archive_message(request)

    assert response["error"] == "Message ID is required"
    assert request.response.status == "400 Bad Request"


def test_send_and_archive_message_empty_message_id():
    """Test send and archive with empty message_id."""
    request = DummyRequest()
    request.matchdict = {"message_id": ""}

    response = server.app.send_and_archive_message(request)

    assert response["error"] == "Message ID is required"
    assert request.response.status == "400 Bad Request"


def test_multiple_messages_share_company_draft(clean_test_db):
    """Test that multiple messages from the same company share the company-level reply draft."""
    repo = clean_test_db

    # Create a company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create two messages for the same company
    message1 = RecruiterMessage(
        message_id="msg1",
        company_id="test-company",
        subject="First Message",
        sender="recruiter1@test.com",
        date=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="First message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread1",
        thread_id="thread1",
    )
    message2 = RecruiterMessage(
        message_id="msg2",
        company_id="test-company",
        subject="Second Message",
        sender="recruiter2@test.com",
        date=datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="Second message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread2",
        thread_id="thread2",
    )

    repo.create_recruiter_message(message1)
    repo.create_recruiter_message(message2)

    # Test GET /api/messages - both messages should have no reply initially
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    assert len(response) == 2
    msg1_data = next(msg for msg in response if msg["message_id"] == "msg1")
    msg2_data = next(msg for msg in response if msg["message_id"] == "msg2")

    assert msg1_data["reply_message"] == ""
    assert msg1_data["reply_status"] == "none"
    assert msg2_data["reply_message"] == ""
    assert msg2_data["reply_status"] == "none"

    # Update reply for message1 - should affect both messages
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "Shared reply for company"})
        request.matchdict = {"message_id": "msg1"}
        response = server.app.update_message_by_id(request)

    assert response["reply_message"] == "Shared reply for company"

    # Verify both messages now show the same reply_message
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    msg1_data = next(msg for msg in response if msg["message_id"] == "msg1")
    msg2_data = next(msg for msg in response if msg["message_id"] == "msg2")

    assert msg1_data["reply_message"] == "Shared reply for company"
    assert msg1_data["reply_status"] == "generated"
    assert msg2_data["reply_message"] == "Shared reply for company"
    assert msg2_data["reply_status"] == "generated"

    # Update reply for message2 - should update the shared draft
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"message": "Updated shared reply"})
        request.matchdict = {"message_id": "msg2"}
        response = server.app.update_message_by_id(request)

    assert response["reply_message"] == "Updated shared reply"

    # Verify both messages show the updated reply
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    msg1_data = next(msg for msg in response if msg["message_id"] == "msg1")
    msg2_data = next(msg for msg in response if msg["message_id"] == "msg2")

    assert msg1_data["reply_message"] == "Updated shared reply"
    assert msg1_data["reply_status"] == "generated"
    assert msg2_data["reply_message"] == "Updated shared reply"
    assert msg2_data["reply_status"] == "generated"


def test_message_reply_generation_affects_company_draft(clean_test_db, mock_task_manager):
    """Test that generating a reply for one message affects all messages from the same company."""
    repo = clean_test_db

    # Create a company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create two messages for the same company
    message1 = RecruiterMessage(
        message_id="msg1",
        company_id="test-company",
        subject="First Message",
        sender="recruiter1@test.com",
        date=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="First message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread1",
        thread_id="thread1",
    )
    message2 = RecruiterMessage(
        message_id="msg2",
        company_id="test-company",
        subject="Second Message",
        sender="recruiter2@test.com",
        date=datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc),
        message="Second message content",
        email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread2",
        thread_id="thread2",
    )

    repo.create_recruiter_message(message1)
    repo.create_recruiter_message(message2)

    # Generate reply for message1
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"message_id": "msg1"}
        response = server.app.generate_message_by_id(request)

    assert "task_id" in response
    assert response["status"] == tasks.TaskStatus.PENDING.value

    # Verify task was created for the company (not message-specific)
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.GENERATE_REPLY,
        {"company_id": "test-company"},
    )

    # Simulate task completion by updating company reply_message
    company.reply_message = "Generated reply for company"
    repo.update(company)

    # Verify both messages now show the generated reply
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_messages(request)

    msg1_data = next(msg for msg in response if msg["message_id"] == "msg1")
    msg2_data = next(msg for msg in response if msg["message_id"] == "msg2")

    assert msg1_data["reply_message"] == "Generated reply for company"
    assert msg1_data["reply_status"] == "generated"
    assert msg2_data["reply_message"] == "Generated reply for company"
    assert msg2_data["reply_status"] == "generated"


# Alias management endpoint tests
def test_create_company_alias_success(clean_test_db):
    """Test successful creation of a company alias via POST /api/companies/:id/aliases."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"alias": "Test Corp"})
        request.matchdict = {"company_id": "test-company"}
        # Pre-seed a conflicting alias in another company to ensure conflicts list is populated
        other = Company(
            company_id="other-co",
            name="Other Co",
            details=CompaniesSheetRow(name="Other Co"),
            status=CompanyStatus(),
        )
        repo.create(other)
        repo.create_alias("other-co", "Test Corp", "manual")

        response = server.app.create_company_alias(request)

    # Verify the response
    assert "id" in response
    assert response["company_id"] == "test-company"
    assert response["alias"] == "Test Corp"
    assert response["normalized_alias"] == "test-corp"
    assert response["source"] == "manual"
    assert response["is_active"] is True
    # Conflicts should include the other company
    assert "conflicts" in response
    assert other.company_id in response["conflicts"]


def test_create_company_alias_conflicts_when_matching_canonical(clean_test_db):
    """Creating an alias that matches another company's canonical name should warn in conflicts."""
    repo = clean_test_db

    # Create companies
    acme = Company(
        company_id="acme",
        name="Acme Corp",
        details=CompaniesSheetRow(name="Acme Corp"),
        status=CompanyStatus(),
    )
    repo.create(acme)

    target = Company(
        company_id="target",
        name="Target Name",
        details=CompaniesSheetRow(name="Target Name"),
        status=CompanyStatus(),
    )
    repo.create(target)

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"alias": "acme corp"})
        request.matchdict = {"company_id": "target"}
        response = server.app.create_company_alias(request)

    assert "conflicts" in response
    assert acme.company_id in response["conflicts"]


def test_create_company_alias_with_canonical_setting(clean_test_db):
    """Test creating an alias and setting it as canonical."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Original Name",
        details=CompaniesSheetRow(name="Original Name"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(
            json_body={"alias": "New Canonical Name", "set_as_canonical": True}
        )
        request.matchdict = {"company_id": "test-company"}
        response = server.app.create_company_alias(request)

    # Verify the alias was created
    assert response["alias"] == "New Canonical Name"

    # Verify the company name was updated
    updated_company = repo.get("test-company")
    assert updated_company.name == "New Canonical Name"
    assert updated_company.details.name == "New Canonical Name"


def test_create_company_alias_without_canonical_setting(clean_test_db):
    """Test creating an alias without setting it as canonical."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Original Name",
        details=CompaniesSheetRow(name="Original Name"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(
            json_body={"alias": "New Alias", "set_as_canonical": False}
        )
        request.matchdict = {"company_id": "test-company"}
        response = server.app.create_company_alias(request)

    # Verify the alias was created
    assert response["alias"] == "New Alias"

    # Verify the company name was NOT updated
    updated_company = repo.get("test-company")
    assert updated_company.name == "Original Name"
    assert updated_company.details.name == "Original Name"


def test_create_company_alias_missing_alias(clean_test_db):
    """Test that creating an alias without the alias field returns 400 error."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company"}
        request.json_body = {"set_as_canonical": True}
        response = server.app.create_company_alias(request)

    # Verify error response
    assert response["error"] == "alias is required"
    assert request.response.status == "400 Bad Request"


def test_create_company_alias_company_not_found(clean_test_db):
    """Test that creating an alias for non-existent company returns 404 error."""
    repo = clean_test_db

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "non-existent-company"}
        request.json_body = {"alias": "Test Corp", "set_as_canonical": True}
        response = server.app.create_company_alias(request)

    # Verify error response
    assert response["error"] == "Company not found"
    assert request.response.status == "404 Not Found"


def test_update_company_alias_success(clean_test_db):
    """Test updating an existing alias."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create an alias
    alias_id = repo.create_alias("test-company", "Original Alias", "manual")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"alias": "Updated Alias"})
        request.matchdict = {"company_id": "test-company", "alias_id": alias_id}
        response = server.app.update_company_alias(request)

    # Verify the response
    assert response["alias"] == "Updated Alias"
    assert response["normalized_alias"] == "updated-alias"


def test_update_company_alias_is_active(clean_test_db):
    """Test updating an alias's active status."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create an alias
    alias_id = repo.create_alias("test-company", "Test Alias", "manual")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"is_active": False})
        request.matchdict = {"company_id": "test-company", "alias_id": alias_id}
        response = server.app.update_company_alias(request)

    # Verify the response
    assert response["is_active"] is False


def test_update_company_alias_no_fields(clean_test_db):
    """Test updating an alias with no fields to update."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create an alias
    alias_id = repo.create_alias("test-company", "Test Alias", "manual")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={})
        request.matchdict = {"company_id": "test-company", "alias_id": alias_id}
        response = server.app.update_company_alias(request)

    # Verify error response
    assert response["error"] == "At least one field to update is required"
    assert request.response.status == "400 Bad Request"


def test_update_company_alias_not_found(clean_test_db):
    """Test updating a non-existent alias."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"alias": "Updated Alias"})
        request.matchdict = {"company_id": "test-company", "alias_id": 999}
        response = server.app.update_company_alias(request)

    # Verify error response
    assert response["error"] == "Alias not found"
    assert request.response.status == "404 Not Found"


def test_update_company_alias_company_not_found(clean_test_db):
    """Test updating an alias for a non-existent company."""
    repo = clean_test_db

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"alias": "Updated Alias"})
        request.matchdict = {"company_id": "non-existent-company", "alias_id": 1}
        response = server.app.update_company_alias(request)

    # Verify error response
    assert response["error"] == "Company not found"
    assert request.response.status == "404 Not Found"


def test_delete_company_alias_success(clean_test_db):
    """Test deactivating an alias."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create an alias
    alias_id = repo.create_alias("test-company", "Test Alias", "manual")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company", "alias_id": alias_id}
        response = server.app.delete_company_alias(request)

    # Verify the response
    assert response["success"] is True
    assert response["message"] == "Alias deactivated"

    # Verify the alias is now inactive
    alias = repo.get_alias(alias_id)
    assert alias["is_active"] is False


def test_delete_company_alias_not_found(clean_test_db):
    """Test deactivating a non-existent alias."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company", "alias_id": 999}
        response = server.app.delete_company_alias(request)

    # Verify error response
    assert response["error"] == "Alias not found"
    assert request.response.status == "404 Not Found"


def test_delete_company_alias_company_not_found(clean_test_db):
    """Test deactivating an alias for a non-existent company."""
    repo = clean_test_db

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "non-existent-company", "alias_id": 1}
        response = server.app.delete_company_alias(request)

    # Verify error response
    assert response["error"] == "Company not found"
    assert request.response.status == "404 Not Found"


def test_get_company_includes_aliases(clean_test_db):
    """Test that GET /api/companies/:id includes aliases field."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Create some aliases
    repo.create_alias("test-company", "Test Corp", "manual")
    repo.create_alias("test-company", "TC", "auto")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company"}
        response = server.app.get_company(request)

    # Verify the response includes aliases
    assert "aliases" in response
    aliases = response["aliases"]
    assert isinstance(aliases, list)
    assert len(aliases) == 2

    # Verify alias structure
    for alias in aliases:
        assert "alias" in alias
        assert "source" in alias
        assert "is_active" in alias
        assert isinstance(alias["alias"], str)
        assert isinstance(alias["source"], str)
        assert isinstance(alias["is_active"], bool)

    # Verify specific aliases
    alias_names = [a["alias"] for a in aliases]
    assert "Test Corp" in alias_names
    assert "TC" in alias_names


def test_get_companies_includes_aliases(clean_test_db):
    """Test that GET /api/companies includes aliases field for each company."""
    repo = clean_test_db

    # Create test companies
    company1 = Company(
        company_id="test-company-1",
        name="Test Company 1",
        details=CompaniesSheetRow(name="Test Company 1"),
        status=CompanyStatus(),
    )
    company2 = Company(
        company_id="test-company-2",
        name="Test Company 2",
        details=CompaniesSheetRow(name="Test Company 2"),
        status=CompanyStatus(),
    )
    repo.create(company1)
    repo.create(company2)

    # Create aliases for company1
    repo.create_alias("test-company-1", "TC1", "manual")
    repo.create_alias("test-company-1", "Test Corp 1", "auto")

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        response = server.app.get_companies(request)

    # Verify response structure
    assert isinstance(response, list)
    assert len(response) == 2

    # Find company1 in response
    company1_response = next(c for c in response if c["company_id"] == "test-company-1")
    company2_response = next(c for c in response if c["company_id"] == "test-company-2")

    # Verify company1 has aliases
    assert "aliases" in company1_response
    aliases = company1_response["aliases"]
    assert isinstance(aliases, list)
    assert len(aliases) == 2

    # Verify alias structure for company1
    for alias in aliases:
        assert "alias" in alias
        assert "source" in alias
        assert "is_active" in alias
        assert isinstance(alias["alias"], str)
        assert isinstance(alias["source"], str)
        assert isinstance(alias["is_active"], bool)

    # Verify specific aliases for company1
    alias_names = [a["alias"] for a in aliases]
    assert "TC1" in alias_names
    assert "Test Corp 1" in alias_names

    # Verify company2 has aliases (should be empty or just seed alias)
    assert "aliases" in company2_response
    company2_aliases = company2_response["aliases"]
    assert isinstance(company2_aliases, list)


def test_create_company_alias_empty_alias(clean_test_db):
    """Test that creating an alias with empty alias field returns 400 error."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company"}
        request.json_body = {"alias": "", "set_as_canonical": True}
        response = server.app.create_company_alias(request)

        # Verify error response
        assert response["error"] == "alias is required"
        assert request.response.status == "400 Bad Request"


def test_create_company_alias_default_set_as_canonical(clean_test_db):
    """Test that set_as_canonical defaults to True when not provided."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company"}
        request.json_body = {
            "alias": "Test Corp"
            # set_as_canonical not provided, should default to True
        }
        response = server.app.create_company_alias(request)

    # Verify successful response
    assert response is not None
    assert "id" in response
    assert response["alias"] == "Test Corp"
    assert response["source"] == "manual"
    assert response["is_active"] is True


def test_create_company_alias_set_as_canonical_false(clean_test_db):
    """Test creating an alias with set_as_canonical=False."""
    repo = clean_test_db

    # Create a test company
    company = Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
        status=CompanyStatus(),
    )
    repo.create(company)

    # Mock the repository
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "test-company"}
        request.json_body = {"alias": "Test Corp", "set_as_canonical": False}
        response = server.app.create_company_alias(request)

    # Verify successful response
    assert response is not None
    assert "id" in response
    assert response["alias"] == "Test Corp"
    assert response["source"] == "manual"
    assert response["is_active"] is True


# Merge endpoints
def test_post_merge_companies_success(clean_test_db, mock_task_manager):
    repo = clean_test_db

    canon = Company(
        company_id="canon", name="Canon", details=CompaniesSheetRow(name="Canon")
    )
    dup = Company(company_id="dup", name="Dup", details=CompaniesSheetRow(name="Dup"))
    repo.create(canon)
    repo.create(dup)

    mock_task_manager.create_task.return_value = "task-merge-1"

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(json_body={"duplicate_company_id": "dup"})
        request.matchdict = {"company_id": "canon"}
        response = server.app.merge_companies(request)

    assert response["task_id"] == "task-merge-1"
    assert response["status"] == tasks.TaskStatus.PENDING.value
    mock_task_manager.create_task.assert_called_once_with(
        tasks.TaskType.MERGE_COMPANIES,
        {"canonical_company_id": "canon", "duplicate_company_id": "dup"},
    )


def test_post_merge_companies_validation_errors(clean_test_db, mock_task_manager):
    repo = clean_test_db

    a = Company(company_id="a", name="A", details=CompaniesSheetRow(name="A"))
    b = Company(company_id="b", name="B", details=CompaniesSheetRow(name="B"))
    repo.create(a)
    repo.create(b)

    with patch("models.company_repository", return_value=repo):
        # Same company
        request = DummyRequest(json_body={"duplicate_company_id": "a"})
        request.matchdict = {"company_id": "a"}
        resp = server.app.merge_companies(request)
        assert resp["error"] == "Cannot merge a company with itself"
        assert request.response.status == "400 Bad Request"

        # Missing duplicate id
        request = DummyRequest(json_body={})
        request.matchdict = {"company_id": "a"}
        resp = server.app.merge_companies(request)
        assert resp["error"] == "duplicate_company_id is required"
        assert request.response.status == "400 Bad Request"

        # Non-existent duplicate
        request = DummyRequest(json_body={"duplicate_company_id": "missing"})
        request.matchdict = {"company_id": "a"}
        resp = server.app.merge_companies(request)
        assert resp["error"] == "Duplicate company not found"
        assert request.response.status == "404 Not Found"

        # Deleted duplicate
        assert repo.soft_delete_company("b") is True
        request = DummyRequest(json_body={"duplicate_company_id": "b"})
        request.matchdict = {"company_id": "a"}
        resp = server.app.merge_companies(request)
        assert resp["error"] == "Duplicate company is deleted"
        assert request.response.status == "400 Bad Request"


def test_get_potential_duplicates(clean_test_db):
    repo = clean_test_db

    acme = Company(
        company_id="acme", name="Acme Corp", details=CompaniesSheetRow(name="Acme Corp")
    )
    dupe = Company(
        company_id="acme-dup", name="Acme", details=CompaniesSheetRow(name="Acme")
    )
    repo.create(acme)
    repo.create(dupe)
    repo.create_alias("acme-dup", "Acme Corp", "manual")

    with patch("models.company_repository", return_value=repo):
        request = DummyRequest()
        request.matchdict = {"company_id": "acme"}
        response = server.app.get_potential_duplicates(request)

    assert isinstance(response, list)
    assert response == ["acme-dup"]
