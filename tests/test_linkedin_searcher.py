from unittest.mock import MagicMock, patch


def make_fake_searcher(results_by_name):
    """Create a fake LinkedInSearcher that returns predefined results based on company name."""

    class FakeSearcher:
        def __init__(self, debug=False, headless=True):
            pass

        def login(self):
            pass

        def search_company_connections(self, name):
            return results_by_name.get(name, [])

        def cleanup(self):
            pass

    return FakeSearcher


@patch("linkedin_searcher.LinkedInSearcher", autospec=True)
@patch("linkedin_searcher.company_repository", autospec=True)
def test_linkedin_canonical_works(repo_factory, searcher_cls):
    """Test that when canonical name works, no alias changes are made."""
    import linkedin_searcher

    results_by_name = {"Acme": [{"name": "John Doe", "title": "Engineer"}]}
    searcher_cls.side_effect = make_fake_searcher(results_by_name)

    repo = MagicMock()
    company_mock = MagicMock()
    company_mock.company_id = "cid1"
    company_mock.name = "Acme"
    repo.get_by_normalized_name.return_value = company_mock
    repo.list_aliases.return_value = [
        {"id": 1, "alias": "Acme Co", "source": "manual", "is_active": True}
    ]
    repo_factory.return_value = repo

    out = linkedin_searcher.main("Acme", debug=False, headless=True)

    assert out == [{"name": "John Doe", "title": "Engineer"}]
    repo.set_alias_as_canonical.assert_not_called()


@patch("linkedin_searcher.LinkedInSearcher", autospec=True)
@patch("linkedin_searcher.company_repository", autospec=True)
def test_linkedin_manual_alias_works(repo_factory, searcher_cls):
    """Test that when canonical fails but manual alias works, it sets the alias as canonical."""
    import linkedin_searcher

    results_by_name = {
        "Acme": [],  # Canonical fails
        "Acme Co": [
            {"name": "Jane Smith", "title": "Senior Engineer"}
        ],  # Manual alias works
    }
    searcher_cls.side_effect = make_fake_searcher(results_by_name)

    repo = MagicMock()
    company_mock = MagicMock()
    company_mock.company_id = "cid1"
    company_mock.name = "Acme"
    repo.get_by_normalized_name.return_value = company_mock
    repo.list_aliases.return_value = [
        {"id": 1, "alias": "Acme Co", "source": "manual", "is_active": True},
        {"id": 2, "alias": "Acme Corp", "source": "auto", "is_active": True},
        {"id": 3, "alias": "Acme Inc", "source": "seed", "is_active": True},
    ]
    repo_factory.return_value = repo

    out = linkedin_searcher.main("Acme", debug=False, headless=True)

    assert out == [{"name": "Jane Smith", "title": "Senior Engineer"}]
    repo.set_alias_as_canonical.assert_called_once_with("cid1", 1)


@patch("linkedin_searcher.LinkedInSearcher", autospec=True)
@patch("linkedin_searcher.company_repository", autospec=True)
def test_linkedin_no_candidates_work(repo_factory, searcher_cls):
    """Test that when no candidates work, it logs error and returns empty list."""
    import linkedin_searcher

    results_by_name = {"Acme": [], "Acme Co": [], "Acme Corp": []}
    searcher_cls.side_effect = make_fake_searcher(results_by_name)

    repo = MagicMock()
    company_mock = MagicMock()
    company_mock.company_id = "cid1"
    company_mock.name = "Acme"
    repo.get_by_normalized_name.return_value = company_mock
    repo.list_aliases.return_value = [
        {"id": 1, "alias": "Acme Co", "source": "manual", "is_active": True},
        {"id": 2, "alias": "Acme Corp", "source": "auto", "is_active": True},
    ]
    repo_factory.return_value = repo

    with patch("builtins.print") as mock_print:
        out = linkedin_searcher.main("Acme", debug=False, headless=True)

    assert out == []
    mock_print.assert_called_with(
        "LinkedIn: no working names for company_id=cid1 (tried: ['Acme', 'Acme Co', 'Acme Corp'])"
    )


@patch("linkedin_searcher.LinkedInSearcher", autospec=True)
@patch("linkedin_searcher.company_repository", autospec=True)
def test_linkedin_unknown_company_fallback(repo_factory, searcher_cls):
    """Test that unknown company falls back to legacy behavior."""
    import linkedin_searcher

    results_by_name = {"SomeCo": [{"name": "Bob Wilson", "title": "Developer"}]}
    searcher_cls.side_effect = make_fake_searcher(results_by_name)

    repo = MagicMock()
    repo.get_by_normalized_name.return_value = None
    repo_factory.return_value = repo

    with patch("builtins.print") as mock_print:
        out = linkedin_searcher.main("SomeCo", debug=False, headless=True)

    assert out == [{"name": "Bob Wilson", "title": "Developer"}]
    # Check that the fallback message was printed (it should be the first print call)
    mock_print.assert_any_call(
        "LinkedIn: company SomeCo not found in repo; using raw name."
    )
    repo.list_aliases.assert_not_called()
    repo.set_alias_as_canonical.assert_not_called()


@patch("linkedin_searcher.LinkedInSearcher", autospec=True)
@patch("linkedin_searcher.company_repository", autospec=True)
def test_linkedin_alias_priority_order(repo_factory, searcher_cls):
    """Test that aliases are tried in correct priority order: manual > auto > seed."""
    import linkedin_searcher

    # Only the auto alias works
    results_by_name = {
        "Acme": [],  # Canonical fails
        "Acme Manual": [],  # Manual fails
        "Acme Auto": [{"name": "Auto Worker", "title": "Engineer"}],  # Auto works
    }
    searcher_cls.side_effect = make_fake_searcher(results_by_name)

    repo = MagicMock()
    company_mock = MagicMock()
    company_mock.company_id = "cid1"
    company_mock.name = "Acme"
    repo.get_by_normalized_name.return_value = company_mock
    repo.list_aliases.return_value = [
        {"id": 1, "alias": "Acme Manual", "source": "manual", "is_active": True},
        {"id": 2, "alias": "Acme Auto", "source": "auto", "is_active": True},
        {"id": 3, "alias": "Acme Seed", "source": "seed", "is_active": True},
    ]
    repo_factory.return_value = repo

    out = linkedin_searcher.main("Acme", debug=False, headless=True)

    assert out == [{"name": "Auto Worker", "title": "Engineer"}]
    repo.set_alias_as_canonical.assert_called_once_with("cid1", 2)
