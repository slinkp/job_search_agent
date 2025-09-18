# Consolidated force flags tests; redundant tests moved from test_research_core_force_contacts.py
import datetime
from argparse import Namespace
from unittest import mock

import pytest

import libjobsearch
import models


class _FakeRepo:
    def create_event(self, event):
        return event

    def list_aliases(self, company_id, active_only=True):
        return []

    def get_by_normalized_name(self, name):
        return None

    def create_alias(self, company_id, alias, source):
        return {"company_id": company_id, "alias": alias, "source": source}


@pytest.fixture(autouse=True)
def _patch_company_repository():
    fake = _FakeRepo()
    with mock.patch("models.company_repository", autospec=True, return_value=fake):
        yield fake


def _make_job_search():
    args = Namespace(
        model=libjobsearch.SONNET_LATEST,
        provider="anthropic",
        rag_message_limit=5,
        recruiter_message_limit=5,
        sheet="test",
        test_messages=None,
    )
    cache_settings = libjobsearch.CacheSettings(no_cache=True)
    return libjobsearch.JobSearch(args, loglevel=0, cache_settings=cache_settings)


def _make_row(name: str = "Acme Co") -> models.CompaniesSheetRow:
    return models.CompaniesSheetRow(
        name=name,
        url="https://example.com",
        updated=datetime.date.today(),
        current_state="10. consider applying",
    )


def test_followup_runs_when_force_contacts_even_if_not_good_fit():
    js = _make_job_search()
    row = _make_row()

    with mock.patch.object(
        libjobsearch.JobSearch, "initial_research_company", autospec=True
    ) as mock_init, mock.patch.object(
        libjobsearch.JobSearch, "is_good_fit", autospec=True, return_value=False
    ) as mock_fit, mock.patch.object(
        libjobsearch.JobSearch,
        "followup_research_company",
        autospec=True,
        side_effect=lambda self, r: r,
    ) as mock_followup, mock.patch.object(
        libjobsearch.JobSearch,
        "research_levels",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ), mock.patch.object(
        libjobsearch.JobSearch,
        "research_compensation",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ):
        mock_init.return_value = (row, [])

        js.research_company("hello", model=js.args.model, force_contacts=True)

        mock_init.assert_called_once()
        mock_fit.assert_called()  # checked at least once
        mock_followup.assert_called_once()


def test_levels_and_comp_run_when_force_levels_even_if_placeholder():
    js = _make_job_search()
    row = _make_row(name="<UNKNOWN placeholder>")

    with mock.patch.object(
        libjobsearch.JobSearch, "initial_research_company", autospec=True
    ) as mock_init, mock.patch.object(
        libjobsearch.JobSearch,
        "_is_company_name_placeholder",
        autospec=True,
        return_value=True,
    ), mock.patch.object(
        libjobsearch.JobSearch,
        "research_levels",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ) as mock_levels, mock.patch.object(
        libjobsearch.JobSearch,
        "research_compensation",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ) as mock_comp, mock.patch.object(
        libjobsearch.JobSearch,
        "is_good_fit",
        autospec=True,
        return_value=False,
    ):
        mock_init.return_value = (row, [])

        js.research_company(
            "hello", model=js.args.model, force_levels=True, do_advanced=True
        )

        # Ensure both research steps were invoked and with force=True
        assert mock_levels.call_count == 1
        assert mock_comp.call_count == 1

        _, kwargs_levels = mock_levels.call_args
        _, kwargs_comp = mock_comp.call_args
        assert kwargs_levels.get("force") is True
        assert kwargs_comp.get("force") is True


def test_behavior_preserved_when_no_flags_and_not_good_fit_and_placeholder():
    js = _make_job_search()
    row = _make_row(name="<UNKNOWN placeholder>")

    with mock.patch.object(
        libjobsearch.JobSearch, "initial_research_company", autospec=True
    ) as mock_init, mock.patch.object(
        libjobsearch.JobSearch,
        "_is_company_name_placeholder",
        autospec=True,
        return_value=True,
    ), mock.patch.object(
        libjobsearch.JobSearch,
        "research_levels",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ) as mock_levels, mock.patch.object(
        libjobsearch.JobSearch,
        "research_compensation",
        autospec=True,
        side_effect=lambda self, r, force=False: r,
    ) as mock_comp, mock.patch.object(
        libjobsearch.JobSearch, "is_good_fit", autospec=True, return_value=False
    ) as mock_fit, mock.patch.object(
        libjobsearch.JobSearch,
        "followup_research_company",
        autospec=True,
        side_effect=lambda self, r: r,
    ) as mock_followup:
        mock_init.return_value = (row, [])

        js.research_company("hello", model=js.args.model, do_advanced=True)

        # Should not force anything
        _, kwargs_levels = mock_levels.call_args
        _, kwargs_comp = mock_comp.call_args
        assert kwargs_levels.get("force") is False
        assert kwargs_comp.get("force") is False

        # Follow-up should not run when not a good fit and no force
        mock_followup.assert_not_called()
