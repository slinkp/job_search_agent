import csv
import datetime
import decimal
from unittest.mock import Mock, patch

import pytest

from models import CompaniesSheetRow, Company, FitCategory
from rate_companies import (
    format_company_info,
    get_user_rating,
    rate_companies,
    save_ratings_to_csv,
)


@pytest.fixture
def sample_company():
    """Create a sample company for testing."""
    return Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(
            name="Test Company",
            type="Public",
            total_comp=decimal.Decimal("440"),
            base=decimal.Decimal("215"),
            rsu=decimal.Decimal("175"),
            bonus=decimal.Decimal("50"),
            remote_policy="hybrid",
            total_size=10000,
            ny_address="123 Test St",
            eng_size=500,
        ),
    )


def test_format_company_info(sample_company):
    """Test that company information is formatted correctly for display."""
    info = format_company_info(sample_company)

    # Check that key information is included
    assert "Test Company" in info
    assert "Public" in info
    assert "$440" in info  # Total comp
    assert "$215" in info  # Base
    assert "$175" in info  # RSU
    assert "$50" in info  # Bonus
    assert "hybrid" in info
    assert "10000" in info  # Total size
    assert "500" in info  # Eng size
    assert "123 Test St" in info


@pytest.mark.parametrize(
    "inputs,expected_category",
    [
        (["1"], FitCategory.GOOD),
        (["2"], FitCategory.BAD),
        (["3"], FitCategory.NEEDS_MORE_INFO),
        (["invalid", "1"], FitCategory.GOOD),
        (["q"], None),
    ],
)
def test_get_user_rating(inputs, expected_category):
    """Test user rating input handling."""
    with patch("builtins.input", side_effect=inputs):
        result = get_user_rating()
        assert result == expected_category


def test_save_ratings_to_csv(tmp_path, sample_company):
    """Test saving company ratings to CSV file."""
    # Set up test data
    sample_company.status.fit_category = FitCategory.GOOD
    sample_company.status.fit_confidence_score = 0.9
    sample_company.status.fit_decision_timestamp = datetime.datetime(
        2024, 1, 1, tzinfo=datetime.timezone.utc
    )

    output_file = tmp_path / "test_ratings.csv"

    # Save to CSV
    save_ratings_to_csv([sample_company], str(output_file))

    # Read and verify CSV contents
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["company_id"] == "test-company"
    assert row["name"] == "Test Company"
    assert row["type"] == "Public"
    assert row["total_comp"] == "440"
    assert row["fit_category"] == "good"
    assert row["fit_confidence"] == "0.9"


@patch("builtins.input")
def test_rate_companies_interactive(mock_input, tmp_path, sample_company):
    """Test the main rating function with simulated user input."""
    mock_input.side_effect = ["1"]  # Rating: good

    output_file = tmp_path / "test_ratings.csv"
    repo = Mock()
    repo.get_all.return_value = [sample_company]

    # Run the rating process
    rate_companies(repo, str(output_file), confidence=0.9)

    # Verify company was updated
    assert sample_company.status.fit_category == FitCategory.GOOD
    assert sample_company.status.fit_confidence_score == 0.9
    assert sample_company.status.fit_decision_timestamp is not None

    # Verify repo was called to update the company
    repo.update.assert_called_once_with(sample_company)

    # Verify CSV was created with the rating
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["company_id"] == "test-company"
    assert row["fit_category"] == "good"


@patch("builtins.input")
def test_rate_companies_quit_early(mock_input, tmp_path, sample_company):
    """Test that the rating process can be quit early."""
    mock_input.side_effect = ["q"]  # Quit immediately

    output_file = tmp_path / "test_ratings.csv"
    repo = Mock()
    repo.get_all.return_value = [sample_company, sample_company]  # Two companies

    # Run the rating process
    rate_companies(repo, str(output_file), confidence=0.9)

    # Verify no companies were updated
    repo.update.assert_not_called()

    # Verify CSV was created but empty (just headers)
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 0  # No data rows, just headers


@patch("builtins.input")
def test_rate_companies_skips_rated(mock_input, tmp_path, sample_company):
    """Test that companies with existing ratings are skipped by default."""
    # Pre-rate the company
    sample_company.status.fit_category = FitCategory.GOOD
    sample_company.status.fit_confidence_score = 0.8
    sample_company.status.fit_decision_timestamp = datetime.datetime.now(
        datetime.timezone.utc
    )

    output_file = tmp_path / "test_ratings.csv"
    repo = Mock()
    repo.get_all.return_value = [sample_company]

    # Run the rating process
    rate_companies(repo, str(output_file))

    # Verify no input was requested (company was skipped)
    mock_input.assert_not_called()

    # Verify company was not updated
    repo.update.assert_not_called()


@patch("builtins.input")
def test_rate_companies_rerate_mode(mock_input, tmp_path, sample_company):
    """Test that re-rate mode only shows previously rated companies."""
    # Create two companies, one rated and one unrated
    rated_company = sample_company
    rated_company.status.fit_category = FitCategory.GOOD
    rated_company.status.fit_confidence_score = 0.8
    rated_company.status.fit_decision_timestamp = datetime.datetime.now(
        datetime.timezone.utc
    )

    unrated_company = Company(
        company_id="unrated-company",
        name="Unrated Company",
        details=CompaniesSheetRow(name="Unrated Company"),
    )

    mock_input.side_effect = ["1"]  # New rating for rated company
    output_file = tmp_path / "test_ratings.csv"
    repo = Mock()
    repo.get_all.return_value = [rated_company, unrated_company]

    # Run the rating process in re-rate mode
    rate_companies(repo, str(output_file), rerate=True)

    # Verify only one input was requested (only rated company shown)
    assert mock_input.call_count == 1

    # Verify only rated company was updated
    repo.update.assert_called_once_with(rated_company)
    assert rated_company.status.fit_category == FitCategory.GOOD

    # Verify unrated company was not touched
    assert unrated_company.status.fit_category is None


@patch("builtins.input")
def test_rate_companies_normal_mode(mock_input, tmp_path, sample_company):
    """Test that normal mode only shows unrated companies."""
    # Create two companies, one rated and one unrated
    rated_company = sample_company
    rated_company.status.fit_category = FitCategory.GOOD
    rated_company.status.fit_confidence_score = 0.8
    rated_company.status.fit_decision_timestamp = datetime.datetime.now(
        datetime.timezone.utc
    )

    unrated_company = Company(
        company_id="unrated-company",
        name="Unrated Company",
        details=CompaniesSheetRow(name="Unrated Company"),
    )

    mock_input.side_effect = ["1"]  # Rating for unrated company
    output_file = tmp_path / "test_ratings.csv"
    repo = Mock()
    repo.get_all.return_value = [rated_company, unrated_company]

    # Run the rating process in normal mode
    rate_companies(repo, str(output_file))

    # Verify only one input was requested (only unrated company shown)
    assert mock_input.call_count == 1

    # Verify only unrated company was updated
    repo.update.assert_called_once_with(unrated_company)
    assert unrated_company.status.fit_category == FitCategory.GOOD

    # Verify rated company was not touched
    assert rated_company.status.fit_category == FitCategory.GOOD
