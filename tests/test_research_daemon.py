from datetime import date
from unittest.mock import Mock, patch

import pytest

import libjobsearch
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
        yield mock.return_value


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
def daemon(args, cache_settings, mock_task_manager, mock_company_repo, mock_jobsearch):
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


def test_do_research_new_company(daemon):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Create actual Company object with real CompaniesSheetRow
    company_details = CompaniesSheetRow(name=company_name)
    company = Company(
        name=company_name,
        details=company_details,
        status=CompanyStatus(research_errors=[]),
    )

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    daemon.jobsearch.research_company.return_value = company

    with patch(
        "libjobsearch.upsert_company_in_spreadsheet", autospec=True
    ) as mock_upsert:
        daemon.do_research(args)

        daemon.jobsearch.research_company.assert_called_once_with(
            company_name, model=daemon.ai_model
        )
        daemon.company_repo.create.assert_called_once_with(company)
        mock_upsert.assert_called_once_with(company.details, daemon.args)


def test_do_research_existing_company(daemon):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Create existing company with initial data
    existing_details = CompaniesSheetRow(name=company_name)
    existing_company = Company(
        name=company_name,
        details=existing_details,
        status=CompanyStatus(research_errors=[]),
        recruiter_message=None,
    )
    daemon.company_repo.get.return_value = existing_company

    # Create new research results
    new_details = CompaniesSheetRow(name=company_name)
    research_result = Company(
        name=company_name, details=new_details, status=CompanyStatus(research_errors=[])
    )
    daemon.jobsearch.research_company.return_value = research_result

    with patch(
        "libjobsearch.upsert_company_in_spreadsheet", autospec=True
    ) as mock_upsert:
        daemon.do_research(args)

        daemon.jobsearch.research_company.assert_called_once_with(
            company_name, model=daemon.ai_model
        )

        # Verify existing company was updated with new details
        assert existing_company.details == new_details
        assert existing_company.status.research_errors == []
        daemon.company_repo.update.assert_called_once_with(existing_company)
        mock_upsert.assert_called_once_with(existing_company.details, daemon.args)


def test_do_send_and_archive(daemon):
    company_name = "Test Corp"
    args = {"company_name": company_name}

    # Create actual Company object
    company = Company(
        name=company_name,
        details=CompaniesSheetRow(name=company_name),
        status=CompanyStatus(),
        reply_message="Test reply",
        message_id="msg123",
        recruiter_message=RecruiterMessage(
            message="Test message",
            email_thread_link="https://example.com/thread123",
            thread_id="thread123",
        ),
    )

    daemon.company_repo.get.return_value = company

    with patch("libjobsearch.send_reply_and_archive", autospec=True) as mock_send:
        mock_send.return_value = True
        daemon.do_send_and_archive(args)

        mock_send.assert_called_once_with(
            message_id=company.message_id,
            thread_id=company.thread_id,
            reply=company.reply_message,
            company_name=company_name,
        )

        assert company.details.current_state == "30. replied to recruiter"
        assert company.details.updated == date.today()
        daemon.company_repo.update.assert_called_once_with(company)


def test_do_send_and_archive_dry_run(daemon):
    daemon.dry_run = True
    company_name = "Test Corp"
    args = {"company_name": company_name}

    company = Company(
        name=company_name,
        details=CompaniesSheetRow(name=company_name),
        status=CompanyStatus(),
        reply_message="Test reply",
        message_id="msg123",
    )

    daemon.company_repo.get.return_value = company

    with patch("libjobsearch.send_reply_and_archive", autospec=True) as mock_send:
        daemon.do_send_and_archive(args)
        mock_send.assert_not_called()
