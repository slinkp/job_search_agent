from datetime import date
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

import libjobsearch
import models
from models import CompaniesSheetRow, Company, CompanyStatus, RecruiterMessage
from research_daemon import ResearchDaemon, TaskStatusContext
from tasks import TaskStatus, TaskType


@pytest.fixture
def mock_task_manager():
    with patch("tasks.TaskManager", autospec=True) as mock:
        yield mock.return_value


@pytest.fixture
def mock_company_repo():
    with patch("models.company_repository", autospec=True) as mock:
        yield mock.return_value


@pytest.fixture
def mock_jobsearch():
    with patch("libjobsearch.JobSearch", autospec=True) as mock:
        instance = mock.return_value
        yield instance


@pytest.fixture
def args():
    mock_args = Mock()
    mock_args.model = "gpt-4"
    mock_args.dry_run = False
    mock_args.no_headless = False
    return mock_args


@pytest.fixture()
def cache_settings():
    return libjobsearch.CacheSettings(
        clear_all_cache=False, clear_cache=[], cache_until=None, no_cache=True
    )


# Always use this mock for all tests
@pytest.fixture(autouse=True)
def mock_spreadsheet_upsert():
    """Fixture to mock spreadsheet upsert operations."""
    with patch("libjobsearch.upsert_company_in_spreadsheet", autospec=True) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_email():
    """Fixture to mock email operations."""
    with patch("libjobsearch.send_reply_and_archive", autospec=True) as mock:
        mock.return_value = True
        yield mock


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


@pytest.fixture
def test_company_with_message(test_company):
    """Fixture to create a test company with a recruiter message."""
    test_company.recruiter_message = RecruiterMessage(
        message="Test message",
        message_id="msg123",
        company_id=test_company.company_id,
        thread_id="thread123",
    )
    return test_company


@pytest.fixture
def test_company_with_reply(test_company_with_message):
    """Fixture to create a test company with a reply message."""
    test_company_with_message.reply_message = "Test reply"
    return test_company_with_message


@pytest.fixture
def test_recruiter_messages():
    """Fixture to create test recruiter messages."""
    return [
        RecruiterMessage(
            message="Job at Acme Corp",
            message_id="msg1",
            thread_id="thread1",
        ),
        RecruiterMessage(
            message="Job at Test Corp",
            message_id="msg2",
            thread_id="thread2",
        ),
    ]


@pytest.fixture
def test_companies():
    """Fixture to create test companies."""
    return [
        Company(
            company_id="acme-corp",
            name="Acme Corp",
            details=CompaniesSheetRow(name="Acme Corp"),
            status=CompanyStatus(),
        ),
        Company(
            company_id="test-corp",
            name="Test Corp",
            details=CompaniesSheetRow(name="Test Corp"),
            status=CompanyStatus(),
        ),
    ]


@pytest.fixture
def mock_spreadsheet_client():
    with patch("spreadsheet_client.MainTabCompaniesClient", autospec=True) as mock:
        yield mock


@pytest.fixture
def daemon(
    args,
    cache_settings,
    mock_task_manager,
    mock_company_repo,
    mock_jobsearch,
    mock_spreadsheet_upsert,
    mock_email,
    mock_spreadsheet_client,
):
    # Configure the mock client to return empty list for read_rows_from_google
    mock_spreadsheet_client.return_value.read_rows_from_google.return_value = []
    daemon = ResearchDaemon(args, cache_settings)
    return daemon


def test_task_status_context_success(mock_task_manager):
    task_id = "123"
    task_type = TaskType.COMPANY_RESEARCH

    with TaskStatusContext(mock_task_manager, task_id, task_type):
        pass

    mock_task_manager.update_task.assert_any_call(task_id, TaskStatus.RUNNING)
    mock_task_manager.update_task.assert_called_with(task_id, TaskStatus.COMPLETED)


def test_task_status_context_failure(mock_task_manager):
    task_id = "123"
    task_type = TaskType.COMPANY_RESEARCH

    with pytest.raises(ValueError):
        with TaskStatusContext(mock_task_manager, task_id, task_type):
            raise ValueError("Test error")

    mock_task_manager.update_task.assert_any_call(task_id, TaskStatus.RUNNING)
    mock_task_manager.update_task.assert_called_with(
        task_id, TaskStatus.FAILED, error="Test error"
    )


def test_process_next_task_no_tasks(daemon):
    daemon.task_mgr.get_next_pending_task.return_value = None
    daemon.process_next_task()
    daemon.task_mgr.get_next_pending_task.assert_called_once()


def test_do_research_new_company(daemon, test_company, mock_spreadsheet_upsert):
    args = {"company_id": "test-corp", "company_name": "Test Corp"}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.return_value = test_company

    daemon.do_research(args)

    assert daemon.jobsearch.research_company.call_count == 1
    # Inspect the call args
    call_args = daemon.jobsearch.research_company.call_args
    assert f"Company name: {test_company.name}" in call_args[0][0]
    assert call_args[1] == {"model": daemon.ai_model}
    daemon.company_repo.create.assert_called_once_with(test_company)
    mock_spreadsheet_upsert.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_existing_company(daemon, test_company, mock_spreadsheet_upsert):
    args = {"company_id": "test-corp", "company_name": "Test Corp"}

    # Create existing company with initial data
    existing_company = test_company
    daemon.company_repo.get.return_value = existing_company

    # Create new research results
    research_result = test_company
    daemon.jobsearch.research_company.return_value = research_result

    daemon.do_research(args)

    assert daemon.jobsearch.research_company.call_count == 1
    # Inspect the call args
    call_args = daemon.jobsearch.research_company.call_args
    assert f"Company name: {test_company.name}" in call_args[0][0]
    assert call_args[1] == {"model": daemon.ai_model}

    # Verify existing company was updated with new details
    assert existing_company.details == research_result.details
    assert existing_company.status.research_errors == []
    daemon.company_repo.update.assert_called_once_with(existing_company)
    mock_spreadsheet_upsert.assert_called_once_with(existing_company.details, daemon.args)


def test_do_research_error_new_company(mock_spreadsheet_upsert, daemon, test_company):
    """Test research error handling for a new company."""
    args = {"company_id": "test-corp", "company_name": "Test Corp"}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.side_effect = ValueError("Research failed")

    # Call the function - it should handle the error internally
    daemon.do_research(args)

    # Verify minimal company was created with error
    assert daemon.company_repo.create.call_count == 1
    error_company = daemon.company_repo.create.call_args[0][0]
    assert error_company.name == test_company.name
    assert "Research failed" in error_company.details.notes
    assert len(error_company.status.research_errors) == 1
    assert error_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in error_company.status.research_errors[0].error

    # Check the spreadsheet update was attempted
    mock_spreadsheet_upsert.assert_called_once_with(error_company.details, daemon.args)


def test_do_send_and_archive(daemon, test_company_with_reply, mock_email):
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = test_company_with_reply
    mock_email.return_value = True

    daemon.do_send_and_archive(args)

    mock_email.assert_called_once_with(
        message_id=test_company_with_reply.recruiter_message.message_id,
        thread_id=test_company_with_reply.recruiter_message.thread_id,
        reply=test_company_with_reply.reply_message,
        company_id="test-corp",
    )

    assert test_company_with_reply.details.current_state == "30. replied to recruiter"
    assert test_company_with_reply.details.updated == date.today()
    daemon.company_repo.update.assert_called_once_with(test_company_with_reply)


def test_do_send_and_archive_dry_run(daemon, test_company_with_reply, mock_email):
    daemon.dry_run = True
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = test_company_with_reply

    daemon.do_send_and_archive(args)
    mock_email.assert_not_called()


def test_do_generate_reply(daemon, test_company_with_message):
    """Test generating a reply for a company."""
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = test_company_with_message
    daemon.jobsearch.generate_reply.return_value = "Generated reply"

    daemon.do_generate_reply(args)

    daemon.jobsearch.generate_reply.assert_called_once_with(
        test_company_with_message.initial_message
    )
    assert test_company_with_message.reply_message == "Generated reply"
    daemon.company_repo.update.assert_called_once_with(test_company_with_message)


def test_do_generate_reply_missing_company(daemon):
    """Test generating a reply when company doesn't exist."""
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = None

    with pytest.raises(AssertionError):
        daemon.do_generate_reply(args)


def test_do_generate_reply_missing_recruiter_message(daemon, test_company):
    """Test generating a reply when company has no recruiter message."""
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = test_company

    with pytest.raises(AssertionError):
        daemon.do_generate_reply(args)


def test_do_find_companies_in_recruiter_messages(
    daemon, test_recruiter_messages, test_companies
):
    """Test finding companies in recruiter messages."""
    args = {"max_messages": 2, "do_research": True}

    daemon.jobsearch.get_new_recruiter_messages.return_value = test_recruiter_messages
    daemon.company_repo.get.return_value = None  # Companies don't exist yet
    # No duplicates by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.side_effect = test_companies
    daemon.running = True  # Ensure daemon stays running

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify messages were fetched
    daemon.jobsearch.get_new_recruiter_messages.assert_called_once_with(max_results=2)

    # Verify each message was processed
    assert daemon.jobsearch.research_company.call_count == 2
    for msg, company in zip(test_recruiter_messages, test_companies):
        daemon.company_repo.create.assert_any_call(company)
    assert daemon.jobsearch.research_company.call_count == 2


def test_do_find_companies_in_recruiter_messages_existing_company(
    daemon, test_recruiter_messages, test_companies
):
    """Test finding companies when some already exist."""
    args = {"max_messages": 2, "do_research": True}

    # First company exists by ID, second doesn't
    daemon.company_repo.get.side_effect = [test_companies[0], None]

    # For the normalization check, make the first one a hit and the second one a miss
    daemon.company_repo.get_by_normalized_name.side_effect = [test_companies[0], None]

    daemon.jobsearch.get_new_recruiter_messages.return_value = test_recruiter_messages
    daemon.jobsearch.research_company.return_value = test_companies[1]
    daemon.running = True  # Ensure daemon stays running

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify only second company was created
    assert daemon.company_repo.create.call_count == 1
    daemon.company_repo.create.assert_called_once_with(test_companies[1])

    # Verify first company was updated with research results
    daemon.company_repo.update.assert_called_once_with(test_companies[0])


def test_do_find_companies_in_recruiter_messages_no_company_name(
    daemon, test_recruiter_messages
):
    """Test finding companies when no company name is extracted."""
    args = {"max_messages": 2, "do_research": True}

    daemon.jobsearch.get_new_recruiter_messages.return_value = [
        test_recruiter_messages[0]
    ]
    daemon.jobsearch.research_company.return_value = Company(
        company_id="unknown",
        name="",
        details=CompaniesSheetRow(name=""),
        status=CompanyStatus(),
    )

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify no company was created
    daemon.company_repo.create.assert_not_called()


def test_do_find_companies_in_recruiter_messages_error(daemon, test_recruiter_messages):
    """Test finding companies when research fails."""
    args = {"max_messages": 2, "do_research": True}

    daemon.jobsearch.get_new_recruiter_messages.return_value = [
        test_recruiter_messages[0]
    ]
    daemon.jobsearch.research_company.side_effect = ValueError("Research failed")

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify no company was created
    daemon.company_repo.create.assert_not_called()


def test_do_find_companies_in_recruiter_messages_no_research(
    daemon, test_recruiter_messages, test_companies
):
    """Test finding companies when do_research=False - should create basic companies without any research."""
    args = {"max_messages": 2, "do_research": False}

    daemon.jobsearch.get_new_recruiter_messages.return_value = test_recruiter_messages
    daemon.company_repo.get_by_normalized_name.return_value = (
        None  # No existing companies
    )
    daemon.running = True  # Ensure daemon stays running

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify messages were fetched
    daemon.jobsearch.get_new_recruiter_messages.assert_called_once_with(max_results=2)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify companies were created using create_basic_company_from_message
    assert daemon.company_repo.create.call_count == 2


def test_do_find_companies_in_recruiter_messages_no_research_existing_company(
    daemon, test_recruiter_messages, test_companies
):
    """Test finding companies when do_research=False and company already exists."""
    args = {"max_messages": 1, "do_research": False}

    daemon.jobsearch.get_new_recruiter_messages.return_value = [
        test_recruiter_messages[0]
    ]
    daemon.running = True  # Ensure daemon stays running

    # Mock that company exists by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = test_companies[0]

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify existing company was updated (not created)
    daemon.company_repo.update.assert_called_once_with(test_companies[0])
    daemon.company_repo.create.assert_not_called()


def test_create_basic_company_from_message_success(
    daemon, test_recruiter_messages, test_companies
):
    """Test creating a basic company from a message without research."""
    message = test_recruiter_messages[0]

    daemon.company_repo.get_by_normalized_name.return_value = None  # No existing company

    result = daemon.create_basic_company_from_message(message)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify company was created
    daemon.company_repo.create.assert_called_once()
    assert result is not None
    assert result.name == f"Company from {message.sender}"


def test_create_basic_company_from_message_existing_company(
    daemon, test_recruiter_messages, test_companies
):
    """Test creating a basic company when company already exists."""
    message = test_recruiter_messages[0]
    existing_company = test_companies[0]

    daemon.company_repo.get_by_normalized_name.return_value = existing_company

    result = daemon.create_basic_company_from_message(message)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify existing company was updated (not created)
    daemon.company_repo.update.assert_called_once_with(existing_company)
    daemon.company_repo.create.assert_not_called()
    assert result == existing_company


def test_create_basic_company_from_message_no_company_name(
    daemon, test_recruiter_messages
):
    """Test creating a basic company when no company name is extracted."""
    message = test_recruiter_messages[0]

    # Ensure no existing company is found
    daemon.company_repo.get_by_normalized_name.return_value = None

    result = daemon.create_basic_company_from_message(message)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify company was created with placeholder name
    daemon.company_repo.create.assert_called_once()
    assert result is not None
    assert result.name == f"Company from {message.sender}"


def test_create_basic_company_from_message_unknown_company_name(
    daemon, test_recruiter_messages
):
    """Test creating a basic company when company name starts with '<UNKNOWN'."""
    message = test_recruiter_messages[0]

    # Ensure no existing company is found
    daemon.company_repo.get_by_normalized_name.return_value = None

    result = daemon.create_basic_company_from_message(message)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify company was created with placeholder name
    daemon.company_repo.create.assert_called_once()
    assert result is not None
    assert result.name == f"Company from {message.sender}"


def test_create_basic_company_from_message_error(daemon, test_recruiter_messages):
    """Test creating a basic company when an error occurs."""
    message = test_recruiter_messages[0]

    # Ensure no existing company is found
    daemon.company_repo.get_by_normalized_name.return_value = None

    # Mock an error in the company creation process
    daemon.company_repo.create.side_effect = ValueError("Database error")

    result = daemon.create_basic_company_from_message(message)

    # Verify NO research was done (research_company should not be called)
    assert daemon.jobsearch.research_company.call_count == 0

    # Verify error was handled gracefully
    assert result is None


def test_do_ignore_and_archive(daemon, test_company):
    """Test ignoring and archiving a company's message."""
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = test_company

    result = daemon.do_ignore_and_archive(args)

    # Verify company was updated
    assert test_company.details.current_state == "70. ruled out, without reply"
    assert test_company.details.updated == date.today()
    daemon.company_repo.update.assert_called_once_with(test_company)

    # Verify event was created
    daemon.company_repo.create_event.assert_called_once()
    event = daemon.company_repo.create_event.call_args[0][0]
    assert event.company_id == test_company.company_id
    assert event.event_type == models.EventType.ARCHIVED

    assert result == {"status": "success"}


def test_do_ignore_and_archive_missing_company(daemon):
    """Test ignoring and archiving when company doesn't exist."""
    args = {"company_id": "test-corp"}

    daemon.company_repo.get.return_value = None

    result = daemon.do_ignore_and_archive(args)

    assert result == {"error": "Company not found"}
    daemon.company_repo.update.assert_not_called()
    daemon.company_repo.create_event.assert_not_called()


def test_do_research_with_url(daemon, test_company, mock_spreadsheet_upsert):
    """Test research using a company URL."""
    args = {"company_url": "https://example.com"}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.return_value = test_company

    daemon.do_research(args)

    assert daemon.jobsearch.research_company.call_count == 1
    # Inspect the call args
    call_args = daemon.jobsearch.research_company.call_args
    assert "Company URL: https://example.com" in call_args[0][0]
    assert call_args[1] == {"model": daemon.ai_model}

    daemon.company_repo.create.assert_called_once_with(test_company)
    mock_spreadsheet_upsert.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_with_url_and_name(daemon, test_company, mock_spreadsheet_upsert):
    """Test research using both URL and company name."""
    args = {"company_url": "https://example.com", "company_name": "Test Corp"}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.return_value = test_company

    daemon.do_research(args)

    assert daemon.jobsearch.research_company.call_count == 1
    # Inspect the call args
    call_args = daemon.jobsearch.research_company.call_args
    assert "Company name: Test Corp" in call_args[0][0]
    assert "Company URL: https://example.com" in call_args[0][0]
    assert call_args[1] == {"model": daemon.ai_model}

    daemon.company_repo.create.assert_called_once_with(test_company)
    mock_spreadsheet_upsert.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_with_unknown_company_name(mock_spreadsheet_upsert, daemon):
    """Test research when no company name is provided."""
    args = {"company_url": "https://example.com"}
    error = ValueError("Research failed")

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.side_effect = error

    # Call the function - it should handle the error internally
    daemon.do_research(args)

    # Verify minimal company was created with error
    assert daemon.company_repo.create.call_count == 1
    error_company = daemon.company_repo.create.call_args[0][0]
    assert error_company.name.startswith("<UNKNOWN")
    assert "Research failed" in error_company.details.notes
    assert len(error_company.status.research_errors) == 1
    assert error_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in error_company.status.research_errors[0].error

    # Check the spreadsheet update was attempted
    mock_spreadsheet_upsert.assert_called_once_with(error_company.details, daemon.args)


def test_generate_company_id(daemon):
    """Test the company ID generation function."""
    assert daemon._generate_company_id("Test Corp") == "test-corp"
    assert daemon._generate_company_id("ACME Corporation") == "acme-corporation"
    assert daemon._generate_company_id("Test Corp!") == "test-corp"
    assert daemon._generate_company_id("  Test Corp  ") == "test-corp"
    assert daemon._generate_company_id("Test & Corp") == "test-and-corp"
    assert daemon._generate_company_id("Test@Corp.com") == "test-corp-com"


def test_do_research_with_normalized_name_duplicate(
    daemon, test_company, mock_spreadsheet_upsert
):
    """Test research when we find a duplicate by normalized name."""
    args = {"company_name": "TEST CORP"}  # Different case but same normalized name

    # Company doesn't exist by ID
    daemon.company_repo.get.return_value = None

    # But exists with normalized name
    existing_company = test_company
    daemon.company_repo.get_by_normalized_name.return_value = existing_company

    # New research results
    new_company = models.Company(
        company_id="test-corp",
        name="TEST CORP",  # Different case
        details=models.CompaniesSheetRow(name="TEST CORP", url="https://example.com"),
        status=models.CompanyStatus(),
    )
    daemon.jobsearch.research_company.return_value = new_company

    daemon.do_research(args)

    # Verify we looked up by normalized name
    daemon.company_repo.get_by_normalized_name.assert_called_once_with("TEST CORP")

    # Verify existing company was updated with new details but not created
    daemon.company_repo.create.assert_not_called()
    daemon.company_repo.update.assert_called_once_with(existing_company)

    # Verify the existing company was updated with the new details
    assert existing_company.details == new_company.details
    # Verify the name was updated to the new name or kept if the new one is empty
    assert existing_company.name == "TEST CORP"

    mock_spreadsheet_upsert.assert_called_once_with(existing_company.details, daemon.args)


@patch("libjobsearch.upsert_company_in_spreadsheet")
def test_do_research_error_with_normalized_name_duplicate(
    mock_spreadsheet_upsert, daemon, test_company
):
    """Test research error handling when we find a duplicate by normalized name."""
    args = {"company_name": "TEST CORP"}

    # Company doesn't exist by ID
    daemon.company_repo.get.return_value = None

    # But exists with normalized name
    existing_company = test_company
    daemon.company_repo.get_by_normalized_name.return_value = existing_company

    # Research fails
    daemon.jobsearch.research_company.side_effect = ValueError("Research failed")

    # Call the function - it should handle the error internally
    result = daemon.do_research(args)

    # Verify existing company was updated with error details but no new company was created
    daemon.company_repo.create.assert_not_called()
    daemon.company_repo.update.assert_called_once_with(existing_company)

    # Verify error was recorded in existing company
    assert len(existing_company.status.research_errors) == 1
    assert existing_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in existing_company.status.research_errors[0].error
    assert "Research failed" in existing_company.details.notes

    # Verify the spreadsheet update was attempted
    mock_spreadsheet_upsert.assert_called_once_with(existing_company.details, daemon.args)

    # Verify the function returned the existing company
    assert result is existing_company


def test_get_content_for_research_with_company(daemon, test_company_with_message):
    """Test get_content_for_research with a company that has name, URL and recruiter message."""
    # Set up test company with URL
    test_company_with_message.details.url = "https://example.com"

    result = daemon.get_content_for_research(
        company=test_company_with_message,
        company_name="",
        company_url="",
        content="",
    )

    assert result["company_name"] == test_company_with_message.name
    assert result["company_url"] == test_company_with_message.details.url
    assert result["content"].startswith(f"Company name: {test_company_with_message.name}")
    assert f"Company URL: {test_company_with_message.details.url}" in result["content"]
    assert test_company_with_message.recruiter_message.message in result["content"]


def test_get_content_for_research_with_name_only(daemon):
    """Test get_content_for_research with only a company name."""
    result = daemon.get_content_for_research(
        company=None,
        company_name="Test Corp",
        company_url="",
        content="",
    )

    assert result["company_name"] == "Test Corp"
    assert result["company_url"] == ""
    assert result["content"] == "Company name: Test Corp"


def test_get_content_for_research_with_url_only(daemon):
    """Test get_content_for_research with only a URL."""
    result = daemon.get_content_for_research(
        company=None,
        company_name="",
        company_url="https://example.com",
        content="",
    )

    assert result["company_name"] == ""
    assert result["company_url"] == "https://example.com"
    assert result["content"] == "Company URL: https://example.com"


def test_get_content_for_research_with_name_and_url(daemon):
    """Test get_content_for_research with both name and URL."""
    result = daemon.get_content_for_research(
        company=None,
        company_name="Test Corp",
        company_url="https://example.com",
        content="",
    )

    assert result["company_name"] == "Test Corp"
    assert result["company_url"] == "https://example.com"
    assert (
        result["content"] == "Company name: Test Corp\n\nCompany URL: https://example.com"
    )


def test_get_content_for_research_with_content(daemon):
    """Test get_content_for_research with custom content."""
    result = daemon.get_content_for_research(
        company=None,
        company_name="Test Corp",
        company_url="https://example.com",
        content="This is a job description for Test Corp.",
    )

    assert result["company_name"] == "Test Corp"
    assert result["company_url"] == "https://example.com"
    assert result["content"].startswith("Company name: Test Corp")
    assert "Company URL: https://example.com" in result["content"]
    assert result["content"].endswith("This is a job description for Test Corp.")


def test_get_content_for_research_with_no_content(daemon):
    """Test get_content_for_research with no searchable content."""
    with pytest.raises(
        ValueError,
        match="No searchable found via any of content, name, url, or existing company",
    ):
        daemon.get_content_for_research(
            company=None,
            company_name="",
            company_url="",
            content="",
        )


def test_get_content_for_research_override_company_details(daemon, test_company):
    """Test get_content_for_research with overridden company details."""
    # Set up test company with URL
    test_company.details.url = "https://example.com"

    result = daemon.get_content_for_research(
        company=test_company,
        company_name="Override Corp",
        company_url="https://override.com",
        content="Custom content",
    )

    assert result["company_name"] == "Override Corp"
    assert result["company_url"] == "https://override.com"
    assert result["content"].startswith("Company name: Override Corp")
    assert "Company URL: https://override.com" in result["content"]
    assert result["content"].endswith("Custom content")


def test_get_content_for_research_whitespace_handling(daemon):
    """Test get_content_for_research with whitespace in inputs."""
    result = daemon.get_content_for_research(
        company=None,
        company_name="  Test Corp  ",
        company_url="  https://example.com  ",
        content="  This is content with whitespace  ",
    )

    assert result["company_name"] == "Test Corp"
    assert result["company_url"] == "https://example.com"
    assert "Company name: Test Corp" in result["content"]
    assert "Company URL: https://example.com" in result["content"]
    assert result["content"].endswith("This is content with whitespace")


@freeze_time("2023-01-15")
def test_do_import_companies_from_spreadsheet(
    daemon, mock_company_repo, mock_spreadsheet_client
):
    """Test importing companies from spreadsheet."""
    mock_client = mock_spreadsheet_client.return_value
    # Setup test data - create mock sheet rows
    sheet_rows = [
        CompaniesSheetRow(
            name="Existing Company",
            type="Tech",
            valuation="1B",
            funding_series="Series B",
            updated=date(2023, 1, 10),  # More recent date than existing company
        ),
        CompaniesSheetRow(
            name="New Company",
            type="AI",
            valuation="500M",
            funding_series="Series A",
            updated=None,  # No date set
        ),
        CompaniesSheetRow(
            name="Error Company",
            type="Healthcare",
            valuation="100M",
            updated=None,  # No date set
        ),
    ]

    # Setup mock client
    mock_client.read_rows_from_google.return_value = sheet_rows

    # Mock existing company in repo with proper date objects
    existing_company = Company(
        company_id="existingcompany",
        name="Existing Company",
        details=CompaniesSheetRow(
            name="Existing Company",
            type="Tech",
            valuation="500M",  # Old value that should be updated
            funding_series="Series B",
            updated=date(2022, 12, 1),  # Older date than in the spreadsheet
        ),
        status=CompanyStatus(),
    )

    # Configure repository mock - first company exists, second doesn't
    def get_side_effect(company_id):
        if company_id == "existingcompany":
            return existing_company
        return None

    def get_by_normalized_name_side_effect(name):
        if "existing" in name.lower():
            return existing_company
        elif "error" in name.lower():
            raise Exception("Test error")
        return None

    mock_company_repo.get.side_effect = get_side_effect
    mock_company_repo.get_by_normalized_name.side_effect = (
        get_by_normalized_name_side_effect
    )

    # Set a fake task context for task_id
    class FakeContext:
        task_id = "test-task-123"

    daemon._current_task_context = FakeContext()

    # Ensure the daemon is in running state
    daemon.running = True

    result = daemon.do_import_companies_from_spreadsheet({})

    # Verify results
    assert result["total_found"] == 3
    assert result["processed"] == 3
    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["errors"] == 1
    assert result["percent_complete"] == 100
    assert "current_company" in result
    assert result["error_details"][0]["company"] == "Error Company"

    # Verify repository interactions
    assert mock_company_repo.get.call_count == 3  # Called for all companies
    assert (
        mock_company_repo.get_by_normalized_name.call_count == 3
    )  # Called for all companies that don't match by get()
    assert mock_company_repo.update.call_count == 1
    assert mock_company_repo.create.call_count == 1

    # Verify company update
    update_call_args = mock_company_repo.update.call_args[0][0]
    assert update_call_args.company_id == "existingcompany"
    assert update_call_args.details.valuation == "1B"  # Should be updated value
    # Should use the newer date from the spreadsheet (2023-01-10), not today's date
    assert update_call_args.details.updated == date(2023, 1, 10)
    assert update_call_args.status.imported_from_spreadsheet is True
    assert update_call_args.status.imported_at is not None

    # Verify company creation for new company with no updated date
    # Should use today's date (2023-01-15) since neither source has an updated date
    create_call_args = mock_company_repo.create.call_args[0][0]
    assert create_call_args.company_id == "new-company"
    assert create_call_args.name == "New Company"
    assert create_call_args.details.type == "AI"
    assert create_call_args.details.valuation == "500M"
    assert create_call_args.details.updated == date(2023, 1, 15)
    assert create_call_args.status.imported_from_spreadsheet is True
    assert create_call_args.status.imported_at is not None


@freeze_time("2023-01-15")
def test_import_progress_tracking(
    daemon, mock_company_repo, mock_spreadsheet_client, monkeypatch
):
    """Test the progress tracking during spreadsheet import."""
    # Mock task_mgr.update_task to capture progress updates
    progress_updates = []

    def mock_update_task(task_id, status, result=None):
        if result:
            progress_updates.append(result.copy())
        return None

    # Patch the update_task method
    monkeypatch.setattr(daemon.task_mgr, "update_task", mock_update_task)

    # Setup test data with 10 companies
    sheet_rows = []
    for i in range(10):
        company_name = f"Company {i+1}"
        sheet_rows.append(
            CompaniesSheetRow(
                name=company_name,
                type="Tech",
            )
        )

    # Mock the spreadsheet client
    mock_client = mock_spreadsheet_client.return_value
    mock_client.read_rows_from_google.return_value = sheet_rows

    # No existing companies in DB - mock both get methods
    mock_company_repo.get.return_value = None
    mock_company_repo.get_by_normalized_name.return_value = None

    # Set a fake task context for task_id
    class FakeContext:
        task_id = "test-task-123"

    daemon._current_task_context = FakeContext()

    # Ensure the daemon is in running state
    daemon.running = True

    # Run the import
    daemon.do_import_companies_from_spreadsheet({})

    # Verify progress updates were made
    assert len(progress_updates) > 0

    # Verify first update has initial state
    assert progress_updates[0]["total_found"] == 10
    assert progress_updates[0]["processed"] == 0
    assert progress_updates[0]["current_company"] is None
    assert progress_updates[0]["percent_complete"] == 0

    # Verify intermediate updates show progress
    middle_update = progress_updates[len(progress_updates) // 2]
    assert 0 < middle_update["processed"] < 10
    assert middle_update["current_company"] is not None
    assert 0 < middle_update["percent_complete"] < 100

    # Verify final update shows completion
    final_update = progress_updates[-1]
    assert final_update["processed"] == 10
    assert final_update["created"] == 10
    assert final_update["percent_complete"] == 100

    # Verify repository interactions
    assert mock_company_repo.get_by_normalized_name.call_count == 10
    assert mock_company_repo.create.call_count == 10


def test_format_import_summary(daemon):
    """Test formatting the import summary."""
    import datetime

    # Create test stats
    start_time = datetime.datetime(2023, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2023, 1, 15, 10, 35, 30, tzinfo=datetime.timezone.utc)

    stats = {
        "total_found": 50,
        "processed": 48,
        "created": 30,
        "updated": 15,
        "skipped": 3,
        "errors": 2,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": (end_time - start_time).total_seconds(),
        "error_details": [
            {"company": "Error Company", "error": "Test error message"},
            {"company": "Another Company", "error": "Another error"},
        ],
    }

    # Get the formatted summary
    summary = daemon.format_import_summary(stats)

    # Verify the summary contains all the key information
    assert "SPREADSHEET IMPORT SUMMARY" in summary
    assert f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}" in summary
    assert f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}" in summary
    assert "Duration: 5.5 minutes" in summary
    assert "Companies found in spreadsheet: 50" in summary
    assert "Companies processed: 48" in summary
    assert "Companies created: 30" in summary
    assert "Companies updated: 15" in summary
    assert "Companies skipped: 3" in summary
    assert "Errors encountered: 2" in summary
    assert "Error details:" in summary
    assert "1. Error Company: Test error message" in summary
    assert "2. Another Company: Another error" in summary

    # Test with no errors
    stats["errors"] = 0
    stats["error_details"] = []
    summary_no_errors = daemon.format_import_summary(stats)
    assert "Error details:" not in summary_no_errors

    # Test with missing end_time
    stats_no_end = {
        "total_found": 50,
        "processed": 48,
        "created": 30,
        "updated": 15,
        "skipped": 3,
        "errors": 0,
        "start_time": start_time,
    }
    summary_auto_end = daemon.format_import_summary(stats_no_end)
    assert "End time:" in summary_auto_end
    assert "Duration:" in summary_auto_end


def test_do_find_companies_in_recruiter_messages_persistence_bug(
    daemon, test_recruiter_messages, test_companies
):
    """Test that reproduces the RecruiterMessage persistence bug.

    This test verifies that when processing recruiter messages, the RecruiterMessage
    objects are properly attached to the Company objects that are created.
    """
    args = {"max_messages": 1, "do_research": True}

    # Use a single test message and company
    test_message = test_recruiter_messages[0]
    test_company = test_companies[0]

    # Mock the research flow but verify the RecruiterMessage is properly handled
    daemon.jobsearch.get_new_recruiter_messages.return_value = [test_message]
    daemon.company_repo.get.return_value = None  # Company doesn't exist yet
    daemon.company_repo.get_by_normalized_name.return_value = None

    # Mock the research to return a company with the recruiter message attached
    def mock_research_company(content_or_message, model):
        # This should be called with the full RecruiterMessage object, not just content
        if isinstance(content_or_message, models.RecruiterMessage):
            # The RecruiterMessage should be properly attached
            company = models.Company(
                company_id=test_company.company_id,
                name=test_company.name,
                details=test_company.details,
                recruiter_message=content_or_message,
            )
            return company
        else:
            # This is the bug case - only content string is passed
            company = models.Company(
                company_id=test_company.company_id,
                name=test_company.name,
                details=test_company.details,
            )
            return company

    daemon.jobsearch.research_company.side_effect = mock_research_company
    daemon.running = True

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify the research was called
    assert daemon.jobsearch.research_company.call_count == 1
    call_args = daemon.jobsearch.research_company.call_args

    # Check what was passed to research_company
    content_or_message = call_args[0][0]

    assert isinstance(
        content_or_message, models.RecruiterMessage
    ), f"Expected RecruiterMessage object, got {type(content_or_message)}: {content_or_message}"

    # Verify the company was created with the recruiter message attached
    assert daemon.company_repo.create.call_count == 1
    created_company = daemon.company_repo.create.call_args[0][0]

    assert created_company.recruiter_message is not None
    assert created_company.recruiter_message.message_id == test_message.message_id


def test_do_research_uses_existing_recruiter_message(
    daemon, test_company_with_message, mock_spreadsheet_upsert
):
    """Test that when researching an existing company with a recruiter_message,
    we use the existing recruiter_message object for research.

    This verifies the logic that preserves recruiter_message context when
    re-researching companies that were previously created from recruiter emails.
    """
    # The company already exists and has a recruiter_message
    existing_company = test_company_with_message
    args = {"company_id": existing_company.company_id}
    existing_recruiter_message = existing_company.recruiter_message

    # Mock that the company exists by company_id
    daemon.company_repo.get.return_value = existing_company

    # Mock the research to verify what gets passed
    def mock_research_company(content_or_message, model):
        # We should get the RecruiterMessage object, not just content string
        if isinstance(content_or_message, models.RecruiterMessage):
            # Return updated company with the recruiter_message preserved
            updated_company = models.Company(
                company_id=existing_company.company_id,
                name=existing_company.name,
                details=existing_company.details,
                recruiter_message=content_or_message,
            )
            return updated_company
        else:
            # This should not happen - we should get RecruiterMessage
            pytest.fail(f"Expected RecruiterMessage, got {type(content_or_message)}")

    daemon.jobsearch.research_company.side_effect = mock_research_company

    # Call do_research with just content (no recruiter_message in args)
    result = daemon.do_research(args)

    # Verify research was called
    assert daemon.jobsearch.research_company.call_count == 1
    call_args = daemon.jobsearch.research_company.call_args

    # Verify that the existing recruiter_message was passed to research, not just content
    content_or_message = call_args[0][0]
    assert isinstance(content_or_message, models.RecruiterMessage)
    assert content_or_message.message_id == existing_recruiter_message.message_id
    assert content_or_message.message == existing_recruiter_message.message

    # Verify the company was updated (not created)
    daemon.company_repo.update.assert_called_once()
    daemon.company_repo.create.assert_not_called()

    # Verify the result has the recruiter_message preserved
    assert result is not None
    assert result.recruiter_message is not None
    assert result.recruiter_message.message_id == existing_recruiter_message.message_id

    # Verify spreadsheet was updated
    mock_spreadsheet_upsert.assert_called_once()


def test_do_research_provided_recruiter_message_takes_precedence(
    daemon, test_company_with_message, mock_spreadsheet_upsert
):
    """Test that when both a recruiter_message is provided in args AND the existing
    company has a recruiter_message, the provided one takes precedence.

    This verifies that explicit recruiter_message args override existing ones.
    """
    # Create a new recruiter message to provide in args
    new_recruiter_message = models.RecruiterMessage(
        message_id="new123",
        company_id=test_company_with_message.company_id,
        message="New recruiter message content",
        thread_id="new_thread",
        sender="new_recruiter@example.com",
    )

    args = {"recruiter_message": new_recruiter_message}

    # The company already exists and has a different recruiter_message
    existing_company = test_company_with_message
    existing_recruiter_message = existing_company.recruiter_message

    # Mock that the company exists by company_id
    daemon.company_repo.get.return_value = existing_company

    # Mock the research to verify what gets passed
    def mock_research_company(content_or_message, model):
        # We should get the new RecruiterMessage object, not the existing one
        if isinstance(content_or_message, models.RecruiterMessage):
            # Return updated company with the new recruiter_message
            updated_company = models.Company(
                company_id=existing_company.company_id,
                name=existing_company.name,
                details=existing_company.details,
                recruiter_message=content_or_message,
            )
            return updated_company
        else:
            # This should not happen - we should get RecruiterMessage
            pytest.fail(f"Expected RecruiterMessage, got {type(content_or_message)}")

    daemon.jobsearch.research_company.side_effect = mock_research_company

    # Call do_research with explicit recruiter_message
    daemon.do_research(args)

    # Verify research was called
    assert daemon.jobsearch.research_company.call_count == 1
    call_args = daemon.jobsearch.research_company.call_args

    # Verify that the provided recruiter_message was used, not the existing one
    content_or_message = call_args[0][0]
    assert isinstance(content_or_message, models.RecruiterMessage)
    assert content_or_message.message_id == new_recruiter_message.message_id
    assert content_or_message.message == new_recruiter_message.message
    # Ensure it's NOT the existing recruiter message
    assert content_or_message.message_id != existing_recruiter_message.message_id
    assert content_or_message.message != existing_recruiter_message.message

    # Verify the company was updated
    daemon.company_repo.update.assert_called_once()
    daemon.company_repo.create.assert_not_called()
