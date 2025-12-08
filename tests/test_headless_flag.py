import argparse

import libjobsearch
import models


class DummyEmailResponseGenerator:
    def __init__(
        self, reply_rag_model, reply_rag_limit, loglevel, cache_settings, provider=None
    ):
        pass

    def get_new_recruiter_messages(self, max_results=100):
        return []

    def generate_reply(self, msg: str) -> str:
        return "ok"


def test_jobsearch_headless_defaults_true(monkeypatch):
    parser = libjobsearch.arg_parser()
    args = parser.parse_args([])  # no --no-headless
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )
    js = libjobsearch.JobSearch(
        args, loglevel=0, cache_settings=libjobsearch.CacheSettings()
    )
    assert js.headless is True


def test_jobsearch_no_headless_sets_visible(monkeypatch):
    parser = libjobsearch.arg_parser()
    args = parser.parse_args(["--no-headless"])
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )
    js = libjobsearch.JobSearch(
        args, loglevel=0, cache_settings=libjobsearch.CacheSettings()
    )
    assert js.headless is False


def make_args(no_headless: bool):
    # Minimal args used by JobSearch
    return argparse.Namespace(
        model=libjobsearch.SONNET_LATEST,
        rag_message_limit=10,
        sheet="test",
        test_messages=None,
        recruiter_message_limit=0,
        no_headless=no_headless,
        no_cache=True,
        clear_cache=[],
        cache_until=None,
        clear_all_cache=False,
        verbose=False,
    )


def test_no_headless_flag_propagates_to_levels(monkeypatch):
    # Avoid Gmail auth during JobSearch init
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )

    def fake_run_in_process(func, *args, **kwargs):
        # The critical assertion: headless must be False when --no-headless is used
        assert "headless" in kwargs, "headless kwarg not passed to levels_searcher"
        assert kwargs["headless"] is False, "headless should be False when --no-headless"
        # Return a plausible levels result
        return ["L5", "L6"]

    monkeypatch.setattr(libjobsearch, "run_in_process", fake_run_in_process)

    args = make_args(no_headless=True)
    cache_settings = libjobsearch.CacheSettings(no_cache=True)
    js = libjobsearch.JobSearch(args, loglevel=0, cache_settings=cache_settings)

    row = models.CompaniesSheetRow(name="Gusto")
    updated = js.research_levels(row)
    # Sanity check: method still sets level_equiv as expected
    assert updated.level_equiv is not None
    assert "L5" in updated.level_equiv


def test_no_headless_flag_propagates_to_compensation(monkeypatch):
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )

    def fake_run_in_process(func, *args, **kwargs):
        assert "headless" in kwargs, "headless kwarg not passed to levels_searcher.main"
        assert kwargs["headless"] is False, "headless should be False when --no-headless"
        # Return a minimal, valid salary data list
        return [
            {"total_comp": 200000, "salary": 150000, "equity": 40000, "bonus": 10000},
            {"total_comp": 220000, "salary": 160000, "equity": 50000, "bonus": 10000},
        ]

    monkeypatch.setattr(libjobsearch, "run_in_process", fake_run_in_process)

    args = make_args(no_headless=True)
    cache_settings = libjobsearch.CacheSettings(no_cache=True)
    js = libjobsearch.JobSearch(args, loglevel=0, cache_settings=cache_settings)

    row = models.CompaniesSheetRow(name="Gusto")
    updated = js.research_compensation(row)
    # Ensure numeric fields were computed and stored in thousands
    assert updated.total_comp is not None
    assert updated.base is not None
    # Values should be in thousands: 210000 average -> 210
    assert updated.total_comp == 210
    # Base: 155000 average -> 155
    assert updated.base == 155
    # RSU: 45000 average -> 45
    assert updated.rsu == 45
    # Bonus: 10000 average -> 10
    assert updated.bonus == 10


def test_no_headless_flag_propagates_to_linkedin(monkeypatch):
    monkeypatch.setattr(
        libjobsearch, "EmailResponseGenerator", DummyEmailResponseGenerator
    )

    def fake_run_in_process(func, *args, **kwargs):
        assert "headless" in kwargs, "headless kwarg not passed to linkedin_searcher.main"
        assert kwargs["headless"] is False, "headless should be False when --no-headless"
        # Return a few fake contacts
        return [
            {"name": "Alice Doe", "title": "Staff Engineer"},
            {"name": "Bob Roe", "title": "Senior Engineer"},
        ]

    monkeypatch.setattr(libjobsearch, "run_in_process", fake_run_in_process)

    args = make_args(no_headless=True)
    cache_settings = libjobsearch.CacheSettings(no_cache=True)
    js = libjobsearch.JobSearch(args, loglevel=0, cache_settings=cache_settings)

    row = models.CompaniesSheetRow(name="Gusto")
    updated = js.followup_research_company(row)
    assert updated.maybe_referrals is not None
    assert "Alice Doe" in updated.maybe_referrals
