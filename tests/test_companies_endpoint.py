from unittest.mock import patch

import pytest
from pyramid.testing import DummyRequest

import server.app
import tasks
from models import CompaniesSheetRow, Company, CompanyStatus


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
    assert request.response.status == "500 Internal Server Error"
