from unittest.mock import Mock, patch

import pytest

from levels_searcher import extract_levels


class TestLevelsSearcherAliasIntegration:
    """Test alias-aware behavior in levels_searcher.extract_levels."""

    @pytest.fixture
    def mock_searcher(self):
        """Mock LevelsFyiSearcher that returns controlled results per company name."""
        mock = Mock()
        mock.find_and_extract_levels = Mock()
        mock.cleanup = Mock()
        return mock

    @pytest.fixture
    def mock_repo(self):
        """Mock company repository with controlled responses."""
        repo = Mock()
        repo.get_by_normalized_name = Mock()
        repo.list_aliases = Mock()
        repo.set_alias_as_canonical = Mock()
        return repo

    @pytest.fixture
    def sample_company(self):
        """Sample company for testing."""
        company = Mock()
        company.company_id = "test-company-123"
        company.name = "Canonical Inc"
        return company

    @pytest.fixture
    def sample_aliases(self):
        """Sample aliases for testing."""
        return [
            {"id": 1, "alias": "ManualCo", "source": "manual", "is_active": True},
            {"id": 2, "alias": "AutoCo", "source": "auto", "is_active": True},
            {"id": 3, "alias": "SeedCo", "source": "seed", "is_active": True},
            {"id": 4, "alias": "InactiveCo", "source": "manual", "is_active": False},
        ]

    def test_canonical_name_works_no_canonical_change(
        self, mock_searcher, mock_repo, sample_company
    ):
        """Test that when canonical name works, no canonical change is made."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        mock_repo.list_aliases.return_value = []
        mock_searcher.find_and_extract_levels.return_value = ["L5", "L6"]

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == ["L5", "L6"]
            mock_searcher.find_and_extract_levels.assert_called_once_with("Canonical Inc")
            mock_repo.set_alias_as_canonical.assert_not_called()
            mock_searcher.cleanup.assert_called_once()

    def test_canonical_fails_manual_alias_works_sets_canonical(
        self, mock_searcher, mock_repo, sample_company, sample_aliases
    ):
        """Test that when canonical fails but manual alias works, canonical is set to that alias."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        mock_repo.list_aliases.return_value = sample_aliases

        # Canonical fails, manual succeeds
        def find_levels_side_effect(name):
            if name == "Canonical Inc":
                return []
            elif name == "ManualCo":
                return ["L4", "L5"]
            else:
                return []

        mock_searcher.find_and_extract_levels.side_effect = find_levels_side_effect

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == ["L4", "L5"]
            # Should try canonical first, then manual alias
            assert mock_searcher.find_and_extract_levels.call_count == 2
            mock_searcher.find_and_extract_levels.assert_any_call("Canonical Inc")
            mock_searcher.find_and_extract_levels.assert_any_call("ManualCo")
            # Should set the manual alias as canonical
            mock_repo.set_alias_as_canonical.assert_called_once_with(
                "test-company-123", 1
            )
            mock_searcher.cleanup.assert_called_once()

    def test_ordering_respected_manual_auto_seed(
        self, mock_searcher, mock_repo, sample_company, sample_aliases
    ):
        """Test that alias ordering is respected: manual > auto > seed."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        mock_repo.list_aliases.return_value = sample_aliases

        # Canonical and manual fail, auto succeeds
        def find_levels_side_effect(name):
            if name in ["Canonical Inc", "ManualCo"]:
                return []
            elif name == "AutoCo":
                return ["L3", "L4"]
            else:
                return []

        mock_searcher.find_and_extract_levels.side_effect = find_levels_side_effect

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == ["L3", "L4"]
            # Should try canonical, manual, then auto (stop at auto)
            assert mock_searcher.find_and_extract_levels.call_count == 3
            mock_searcher.find_and_extract_levels.assert_any_call("Canonical Inc")
            mock_searcher.find_and_extract_levels.assert_any_call("ManualCo")
            mock_searcher.find_and_extract_levels.assert_any_call("AutoCo")
            # Should NOT try seed alias
            seed_calls = [
                call
                for call in mock_searcher.find_and_extract_levels.call_args_list
                if call[0][0] == "SeedCo"
            ]
            assert len(seed_calls) == 0, "SeedCo should not have been called"
            # Should set the auto alias as canonical
            mock_repo.set_alias_as_canonical.assert_called_once_with(
                "test-company-123", 2
            )
            mock_searcher.cleanup.assert_called_once()

    def test_no_alias_works_logs_error(
        self, mock_searcher, mock_repo, sample_company, sample_aliases, caplog
    ):
        """Test that when no alias works, an error is logged and no canonical change is made."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        mock_repo.list_aliases.return_value = sample_aliases
        mock_searcher.find_and_extract_levels.return_value = []  # All attempts fail

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == []
            # Should try all candidates
            expected_calls = ["Canonical Inc", "ManualCo", "AutoCo", "SeedCo"]
            assert mock_searcher.find_and_extract_levels.call_count == len(expected_calls)
            for call in expected_calls:
                mock_searcher.find_and_extract_levels.assert_any_call(call)
            # Should not set any alias as canonical
            mock_repo.set_alias_as_canonical.assert_not_called()
            # Should log an error
            assert (
                "Levels: no working names found for company_id=test-company-123"
                in caplog.text
            )
            mock_searcher.cleanup.assert_called_once()

    def test_company_unknown_in_repo_legacy_behavior(self, mock_searcher, mock_repo):
        """Test fallback to legacy behavior when company is unknown in repository."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = None
        mock_searcher.find_and_extract_levels.return_value = ["L5", "L6"]

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Unknown Company")

            # Assert
            assert result == ["L5", "L6"]
            # Should only try the original name
            mock_searcher.find_and_extract_levels.assert_called_once_with(
                "Unknown Company"
            )
            # Should not interact with repository for aliases
            mock_repo.list_aliases.assert_not_called()
            mock_repo.set_alias_as_canonical.assert_not_called()
            mock_searcher.cleanup.assert_called_once()

    def test_inactive_aliases_ignored(self, mock_searcher, mock_repo, sample_company):
        """Test that inactive aliases are ignored."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        # Only inactive aliases
        mock_repo.list_aliases.return_value = [
            {"id": 4, "alias": "InactiveCo", "source": "manual", "is_active": False},
        ]
        mock_searcher.find_and_extract_levels.return_value = []  # All attempts fail

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == []
            # Should only try canonical name, not inactive aliases
            mock_searcher.find_and_extract_levels.assert_called_once_with("Canonical Inc")
            mock_repo.set_alias_as_canonical.assert_not_called()

    def test_duplicate_canonical_name_handled(
        self, mock_searcher, mock_repo, sample_company
    ):
        """Test that if canonical name equals an alias, it's not tried twice."""
        # Arrange
        mock_repo.get_by_normalized_name.return_value = sample_company
        # Include canonical name as an alias
        mock_repo.list_aliases.return_value = [
            {"id": 1, "alias": "Canonical Inc", "source": "manual", "is_active": True},
        ]
        mock_searcher.find_and_extract_levels.return_value = ["L5", "L6"]

        with patch(
            "levels_searcher.LevelsFyiSearcher", return_value=mock_searcher
        ), patch("levels_searcher.company_repository", return_value=mock_repo):

            # Act
            result = extract_levels("Canonical Inc")

            # Assert
            assert result == ["L5", "L6"]
            # Should only try canonical name once
            mock_searcher.find_and_extract_levels.assert_called_once_with("Canonical Inc")
            mock_repo.set_alias_as_canonical.assert_not_called()
