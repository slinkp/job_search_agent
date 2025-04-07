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
def mock_spreadsheet():
    """Fixture to mock spreadsheet operations."""
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
def daemon(
    args,
    cache_settings,
    mock_task_manager,
    mock_company_repo,
    mock_jobsearch,
    mock_spreadsheet,
    mock_email,
):
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
    mock_spreadsheet.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_existing_company(daemon, test_company, mock_spreadsheet):
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
    mock_spreadsheet.assert_called_once_with(existing_company.details, daemon.args)


def test_do_research_error_new_company(daemon, test_company, mock_spreadsheet):
    """Test research error handling for a new company."""
    args = {"company_id": "test-corp", "company_name": "Test Corp"}

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.side_effect = ValueError("Research failed")

    with pytest.raises(ValueError):
        daemon.do_research(args)

    # Verify minimal company was created with error
    assert daemon.company_repo.create.call_count == 1
    created_company = daemon.company_repo.create.call_args[0][0]
    assert created_company.name == test_company.name
    assert "Research failed" in created_company.details.notes
    assert len(created_company.status.research_errors) == 1
    assert created_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in created_company.status.research_errors[0].error
    mock_spreadsheet.assert_called_once_with(created_company.details, daemon.args)


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


def test_do_research_with_url(daemon, test_company, mock_spreadsheet):
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
    mock_spreadsheet.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_with_url_and_name(daemon, test_company, mock_spreadsheet):
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
    mock_spreadsheet.assert_called_once_with(test_company.details, daemon.args)


def test_do_research_with_unknown_company_name(daemon, mock_spreadsheet):
    """Test research when no company name is provided."""
    args = {"company_url": "https://example.com"}
    error = ValueError("Research failed")

    # Company doesn't exist yet
    daemon.company_repo.get.return_value = None
    # No duplicate by normalized name
    daemon.company_repo.get_by_normalized_name.return_value = None
    daemon.jobsearch.research_company.side_effect = error

    with pytest.raises(ValueError):
        daemon.do_research(args)

    # Verify minimal company was created with error
    assert daemon.company_repo.create.call_count == 1
    created_company = daemon.company_repo.create.call_args[0][0]
    assert created_company.name.startswith("<UNKNOWN")
    assert "Research failed" in created_company.details.notes
    assert len(created_company.status.research_errors) == 1
    assert created_company.status.research_errors[0].step == "research_company"
    assert "Research failed" in created_company.status.research_errors[0].error
    mock_spreadsheet.assert_called_once_with(created_company.details, daemon.args)


def test_generate_company_id(daemon):
    """Test the company ID generation function."""
    assert daemon._generate_company_id("Test Corp") == "test-corp"
    assert daemon._generate_company_id("ACME Corporation") == "acme-corporation"
    assert daemon._generate_company_id("Test Corp!") == "test-corp!"
    assert daemon._generate_company_id("  Test Corp  ") == "test-corp"


def test_do_research_with_normalized_name_duplicate(
    daemon, test_company, mock_spreadsheet
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

    mock_spreadsheet.assert_called_once_with(existing_company.details, daemon.args)


def test_do_research_error_with_normalized_name_duplicate(
    daemon, test_company, mock_spreadsheet
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

    with pytest.raises(ValueError):
        daemon.do_research(args)

    # Verify existing company was updated with error details but no new company was created
    daemon.company_repo.create.assert_not_called()
    # Verify the existing company was updated at least once.
    assert daemon.company_repo.update.call_count >= 1

    # Verify error was recorded in existing company
    assert "Research failed" in existing_company.status.research_errors[0].error
    mock_spreadsheet.assert_called_once_with(existing_company.details, daemon.args)


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
def test_do_import_companies_from_spreadsheet(daemon, mock_company_repo):
    """Test importing companies from spreadsheet."""
    # Mock the MainTabCompaniesClient
    with patch("research_daemon.MainTabCompaniesClient") as mock_client_class:
        # Setup test data - create mock sheet rows
        sheet_rows = [
            CompaniesSheetRow(
                name="Existing Company",
                type="Tech",
                valuation="1B",
                funding_series="Series B",
            ),
            CompaniesSheetRow(
                name="New Company", type="AI", valuation="500M", funding_series="Series A"
            ),
            CompaniesSheetRow(name="Error Company", type="Healthcare", valuation="100M"),
        ]

        # Setup mock client
        mock_client = mock_client_class.return_value
        mock_client.read_rows_from_google.return_value = sheet_rows

        # Mock existing company in repo
        existing_company = Company(
            company_id="existingcompany",
            name="Existing Company",
            details=CompaniesSheetRow(
                type="Tech",
                valuation="500M",  # Old value that should be updated
                funding_series="Series B",
                updated=date(2022, 12, 1),
            ),
            status=CompanyStatus(),
        )

        # Configure repository mock - first company exists, second doesn't
        def get_by_normalized_name_side_effect(name):
            if "existing" in name.lower():
                return existing_company
            elif "error" in name.lower():
                raise Exception("Test error")
            return None

        mock_company_repo.get_by_normalized_name.side_effect = (
            get_by_normalized_name_side_effect
        )

        # Set daemon to running mode to prevent early termination
        daemon.running = True

        # Run the import task
        result = daemon.do_import_companies_from_spreadsheet({})

        # Verify results
        assert result["total_found"] == 3
        assert result["processed"] == 3
        assert result["created"] == 1
        assert result["updated"] == 1
        assert result["errors"] == 1

        # Verify repository interactions
        assert mock_company_repo.get_by_normalized_name.call_count == 3
        assert mock_company_repo.update.call_count == 1
        assert mock_company_repo.create.call_count == 1

        # Verify company update
        update_call_args = mock_company_repo.update.call_args[0][0]
        assert update_call_args.company_id == "existingcompany"
        assert update_call_args.details.valuation == "1B"  # Should be updated value
        assert update_call_args.details.updated == date(2023, 1, 15)

        # Verify company creation
        create_call_args = mock_company_repo.create.call_args[0][0]
        assert create_call_args.company_id == "new-company"
        assert create_call_args.name == "New Company"
        assert create_call_args.details.type == "AI"
        assert create_call_args.details.valuation == "500M"
        assert create_call_args.details.updated == date(2023, 1, 15)

        # Verify notes contain import info
        assert "Imported from spreadsheet on 2023-01-15" in create_call_args.details.notes
