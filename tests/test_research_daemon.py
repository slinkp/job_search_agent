from datetime import date
from unittest.mock import Mock, patch

import pytest

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
        instance.send_reply_and_archive = Mock(return_value=True)
        yield instance


@pytest.fixture
def args():
    mock_args = Mock()
    mock_args.model = "gpt-4"
    mock_args.dry_run = False
    mock_args.no_headless = False
    return mock_args


@pytest.fixture
def cache_settings():
    return libjobsearch.CacheSettings(
        clear_all_cache=False, clear_cache=[], cache_until=None, no_cache=False
    )


@pytest.fixture
def mock_spreadsheet():
    """Fixture to mock spreadsheet operations."""
    with patch("libjobsearch.upsert_company_in_spreadsheet", autospec=True) as mock:
        yield mock


@pytest.fixture
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
def daemon(args, cache_settings, mock_task_manager, mock_company_repo, mock_jobsearch):
    with patch("libjobsearch.MainTabCompaniesClient", autospec=True) as mock_client:
        # Configure the mock client to return empty list for read_rows_from_google
        mock_client.return_value.read_rows_from_google.return_value = []
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


def test_do_research_new_company(daemon, test_company, mock_spreadsheet):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    daemon.jobsearch.research_company.return_value = test_company

    daemon.do_research(args)

    daemon.jobsearch.research_company.assert_called_once_with(
        company_name, model=daemon.ai_model
    )
    daemon.company_repo.create.assert_called_once_with(test_company)
    mock_spreadsheet.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_existing_company(daemon, test_company, mock_spreadsheet):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Create existing company with initial data
    existing_company = test_company
    daemon.company_repo.get.return_value = existing_company

    # Create new research results
    research_result = test_company
    daemon.jobsearch.research_company.return_value = research_result

    daemon.do_research(args)

    daemon.jobsearch.research_company.assert_called_once_with(
        company_name, model=daemon.ai_model
    )

    # Verify existing company was updated with new details
    assert existing_company.details == research_result.details
    assert existing_company.status.research_errors == []
    daemon.company_repo.update.assert_called_once_with(existing_company)
    mock_spreadsheet.assert_called_once_with(existing_company.details, daemon.args)


def test_do_research_error_new_company(daemon, test_company, mock_spreadsheet):
    """Test research error handling for a new company."""
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    daemon.jobsearch.research_company.side_effect = ValueError("Research failed")

    with pytest.raises(ValueError):
        daemon.do_research(args)

    # Verify minimal company was created with error
    assert daemon.company_repo.create.call_count == 1
    created_company = daemon.company_repo.create.call_args[0][0]
    assert created_company.name == company_name
    assert "Research failed" in created_company.details.notes
    assert len(created_company.status.research_errors) == 1
    assert created_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in created_company.status.research_errors[0].error
    mock_spreadsheet.assert_called_once_with(created_company.details, daemon.args)


def test_do_send_and_archive(daemon, test_company_with_reply):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    daemon.company_repo.get.return_value = test_company_with_reply

    daemon.do_send_and_archive(args)

    daemon.jobsearch.send_reply_and_archive.assert_called_once_with(
        message_id=test_company_with_reply.recruiter_message.message_id,
        thread_id=test_company_with_reply.recruiter_message.thread_id,
        reply=test_company_with_reply.reply_message,
        company_name=company_name,
    )

    assert test_company_with_reply.details.current_state == "30. replied to recruiter"
    assert test_company_with_reply.details.updated == date.today()
    daemon.company_repo.update.assert_called_once_with(test_company_with_reply)


def test_do_send_and_archive_dry_run(daemon, test_company_with_reply, mock_email):
    daemon.dry_run = True
    company_name = "Test Corp"
    args = {"company_name": company_name}

    daemon.company_repo.get.return_value = test_company_with_reply

    daemon.do_send_and_archive(args)
    mock_email.assert_not_called()


def test_do_generate_reply(daemon, test_company_with_message):
    """Test generating a reply for a company."""
    company_name = "Test Corp"
    args = {"company_name": company_name}

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
    company_name = "Test Corp"
    args = {"company_name": company_name}

    daemon.company_repo.get.return_value = None

    with pytest.raises(AssertionError):
        daemon.do_generate_reply(args)


def test_do_generate_reply_missing_recruiter_message(daemon, test_company):
    """Test generating a reply when company has no recruiter message."""
    company_name = "Test Corp"
    args = {"company_name": company_name}

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
    daemon.jobsearch.research_company.side_effect = test_companies
    daemon.running = True  # Ensure daemon stays running

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify messages were fetched
    daemon.jobsearch.get_new_recruiter_messages.assert_called_once_with(max_results=2)

    # Verify each message was processed
    assert daemon.jobsearch.research_company.call_count == 2
    for msg, company in zip(test_recruiter_messages, test_companies):
        daemon.jobsearch.research_company.assert_any_call(
            msg, model=daemon.ai_model, do_advanced=True
        )
        daemon.company_repo.create.assert_any_call(company)


def test_do_find_companies_in_recruiter_messages_existing_company(
    daemon, test_recruiter_messages, test_companies
):
    """Test finding companies when some already exist."""
    args = {"max_messages": 2, "do_research": True}

    # First company exists, second doesn't
    daemon.company_repo.get.side_effect = [test_companies[0], None]

    daemon.jobsearch.get_new_recruiter_messages.return_value = test_recruiter_messages
    daemon.jobsearch.research_company.return_value = test_companies[1]
    daemon.running = True  # Ensure daemon stays running

    daemon.do_find_companies_in_recruiter_messages(args)

    # Verify only second company was created
    assert daemon.company_repo.create.call_count == 1
    daemon.company_repo.create.assert_called_once()


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


def test_do_ignore_and_archive(daemon, test_company):
    """Test ignoring and archiving a company's message."""
    company_name = "Test Corp"
    args = {"company_name": company_name}

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
    company_name = "Test Corp"
    args = {"company_name": company_name}

    daemon.company_repo.get.return_value = None

    result = daemon.do_ignore_and_archive(args)

    assert result == {"error": "Company not found"}
    daemon.company_repo.update.assert_not_called()
    daemon.company_repo.create_event.assert_not_called()
