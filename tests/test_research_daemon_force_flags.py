import types
import pytest

import research_daemon as rd


class FakeTaskManager:
    def __init__(self, task_args):
        self._first = True
        self._args = task_args
        self.updates = []

    def get_next_pending_task(self):
        if self._first:
            self._first = False
            return ("task-1", rd.TaskType.COMPANY_RESEARCH, self._args)
        return None

    def update_task(self, task_id, status, result=None, error=""):
        # Record status updates for debugging/verification
        self.updates.append(
            {"task_id": task_id, "status": status, "result": result, "error": error}
        )


class FakeRepo:
    def get(self, company_id):
        return None

    def get_by_normalized_name(self, company_name):
        return None

    def update(self, company):
        return True

    def create(self, company):
        return True

    def find_potential_duplicates(self, company_id):
        return []


class FakeJobSearch:
    instances: list["FakeJobSearch"] = []

    def __init__(self, *args, **kwargs):
        self.calls = []
        FakeJobSearch.instances.append(self)

    def research_company(self, message, model, **kwargs):
        # Record call details for assertions
        self.calls.append({"args": (message, model), "kwargs": kwargs})
        # Return a minimal company-like object
        status = types.SimpleNamespace(research_errors=[])
        details = types.SimpleNamespace()
        return types.SimpleNamespace(
            company_id="co-x", name="Acme", details=details, status=status
        )


@pytest.mark.parametrize(
    "task_body,expected",
    [
        ({"content": "hello"}, {"force_levels": False, "force_contacts": False}),
        (
            {"content": "hello", "force_levels": True},
            {"force_levels": True, "force_contacts": False},
        ),
        (
            {"content": "hello", "force_contacts": True},
            {"force_levels": False, "force_contacts": True},
        ),
        (
            {"content": "hello", "force_levels": True, "force_contacts": True},
            {"force_levels": True, "force_contacts": True},
        ),
    ],
)
def test_daemon_passes_force_flags_to_jobsearch(monkeypatch, task_body, expected):
    # Arrange: fake singleton providers and dependencies
    fake_tm = FakeTaskManager(task_body)
    fake_repo = FakeRepo()

    # Patch singleton factories used by ResearchDaemon
    monkeypatch.setattr(rd, "task_manager", lambda: fake_tm)
    monkeypatch.setattr(rd.models, "company_repository", lambda: fake_repo)

    # Patch JobSearch and spreadsheet upsert to avoid side effects
    monkeypatch.setattr(rd.libjobsearch, "JobSearch", FakeJobSearch)
    monkeypatch.setattr(
        rd.libjobsearch, "upsert_company_in_spreadsheet", lambda *a, **k: None
    )

    # Minimal args namespace required by ResearchDaemon
    args = types.SimpleNamespace(model="test-model", dry_run=True, no_headless=True)

    # Cache settings can be a simple namespace; not used in this test
    cache_settings = types.SimpleNamespace()

    daemon = rd.ResearchDaemon(args, cache_settings)

    # Act: process a single task
    daemon.process_next_task()

    # Assert: JobSearch.research_company was called with the expected flags
    assert FakeJobSearch.instances, "JobSearch should have been instantiated"
    calls = FakeJobSearch.instances[0].calls
    assert calls, "research_company should have been called"
    kwargs = calls[0]["kwargs"]
    assert kwargs.get("force_levels", False) is expected["force_levels"]
    assert kwargs.get("force_contacts", False) is expected["force_contacts"]
