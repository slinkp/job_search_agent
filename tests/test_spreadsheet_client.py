from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from models import CompaniesSheetRow
from spreadsheet_client import MainTabCompaniesClient


@pytest.fixture
def mock_sheets_service():
    with patch("spreadsheet_client.build", autospec=True) as mock_build:
        # Sadly, google's very dynamic code means there's
        # no concrete type we can use for a spec.
        mock_service = MagicMock()
        mock_values = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value = mock_values
        mock_build.return_value = mock_service
        yield mock_values


@pytest.fixture
def mock_auth():
    with patch("spreadsheet_client.authorize") as mock_auth:
        mock_auth.return_value = "mock_credentials"
        yield mock_auth


def test_read_rows_from_google(mock_sheets_service, mock_auth):
    """Test that read_rows_from_google fetches data from Google Sheets and converts it to CompaniesSheetRow objects."""
    # Setup mock response from Google Sheets API
    mock_response = {
        "values": [
            [
                "Company A",
                "Public",
                "10B",
                "",
                "",
                "https://companya.com",
                "10. consider applying",
                "2023-01-01",
            ],
            [
                "Company B",
                "Startup",
                "100M",
                "Series C",
                "",
                "https://companyb.com",
                "20. interviewing",
                "2023-02-15",
            ],
        ]
    }
    mock_sheets_service.get.return_value.execute.return_value = mock_response

    # Create the client
    client = MainTabCompaniesClient(
        doc_id="test_doc_id",
        sheet_id="test_sheet_id",
        range_name="Test!A1:Z100",
    )

    result = client.read_rows_from_google()

    mock_sheets_service.get.assert_called_once_with(
        spreadsheetId="test_doc_id", range="Test!A1:Z100"
    )

    assert all(isinstance(row, CompaniesSheetRow) for row in result)
    assert len(result) == 2

    row1 = cast(CompaniesSheetRow, result[0])
    row2 = cast(CompaniesSheetRow, result[1])
    # Verify the first row data was correctly parsed
    assert row1.name == "Company A"
    assert row1.type == "Public"
    assert row1.valuation == "10B"
    assert row1.url == "https://companya.com"
    assert row1.current_state == "10. consider applying"

    assert row2.name == "Company B"
    assert row2.type == "Startup"
    assert row2.valuation == "100M"
    assert row2.funding_series == "Series C"
    assert row2.url == "https://companyb.com"
    assert row2.current_state == "20. interviewing"


def test_read_rows_from_google_empty_sheet(mock_sheets_service, mock_auth):
    """Test reading from an empty sheet."""
    # Setup mock response with no values
    mock_response = {}
    mock_sheets_service.get.return_value.execute.return_value = mock_response

    client = MainTabCompaniesClient(
        doc_id="test_doc_id",
        sheet_id="test_sheet_id",
        range_name="Test!A1:Z100",
    )

    result = client.read_rows_from_google()

    mock_sheets_service.get.assert_called_once_with(
        spreadsheetId="test_doc_id", range="Test!A1:Z100"
    )

    assert result == []
