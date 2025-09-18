import types
import pytest

import libjobsearch as lj
import models


class FakeRepo:
    def create_event(self, event):
        return True

    # Minimal API used in _is_company_name_placeholder path (not used here)
    def get_by_normalized_name(self, name):
        return None

    def list_aliases(self, company_id, active_only=True):
        return []


@pytest.fixture(autouse=True)
def no_db_events(monkeypatch):
    # Avoid touching real DB in tests
    fake_repo = FakeRepo()
    monkeypatch.setattr(models, "company_repository", lambda: fake_repo)
    yield


def make_jobsearch():
    args = types.SimpleNamespace(
        model="test-model",
        rag_message_limit=10,
        provider=None,
        clear_all_cache=False,
        clear_cache=[],
        cache_until=None,
        no_cache=True,
    )
    cache_settings = lj.CacheSettings(no_cache=True)
    return lj.JobSearch(args, loglevel=0, cache_settings=cache_settings)


def test_followup_runs_when_force_contacts_true(monkeypatch):
    js = make_jobsearch()

    # Return a non-placeholder name to avoid placeholder guards
    row = models.CompaniesSheetRow(name="Acme Corp")

    # Patch research steps to be no-ops
    monkeypatch.setattr(
        lj.JobSearch, "initial_research_company", lambda self, message, model: (row, [])
    )
    monkeypatch.setattr(lj.JobSearch, "research_levels", lambda self, r: r)
    monkeypatch.setattr(lj.JobSearch, "research_compensation", lambda self, r: r)

    # Simulate not a good fit
    monkeypatch.setattr(lj.JobSearch, "is_good_fit", lambda self, r: False)

    calls = {"count": 0}

    def fake_followup(self, r):
        calls["count"] += 1
        return r

    monkeypatch.setattr(lj.JobSearch, "followup_research_company", fake_followup)

    js.research_company("msg", model="m", force_contacts=True)

    assert (
        calls["count"] == 1
    ), "followup should run when force_contacts=True even if not a good fit"


def test_followup_not_run_when_force_contacts_false(monkeypatch):
    js = make_jobsearch()

    row = models.CompaniesSheetRow(name="Acme Corp")

    monkeypatch.setattr(
        lj.JobSearch, "initial_research_company", lambda self, message, model: (row, [])
    )
    monkeypatch.setattr(lj.JobSearch, "research_levels", lambda self, r: r)
    monkeypatch.setattr(lj.JobSearch, "research_compensation", lambda self, r: r)
    monkeypatch.setattr(lj.JobSearch, "is_good_fit", lambda self, r: False)

    calls = {"count": 0}

    def fake_followup(self, r):
        calls["count"] += 1
        return r

    monkeypatch.setattr(lj.JobSearch, "followup_research_company", fake_followup)

    js.research_company("msg", model="m", force_contacts=False)

    assert (
        calls["count"] == 0
    ), "followup should not run when force_contacts=False and not a good fit"
