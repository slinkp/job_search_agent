# Feature process! Prrt!
import types
import pytest

import server.app as app_module


class DummyResponse:
    def __init__(self):
        self.status = 200


def make_request(company_id: str, body):
    # Simple dummy request carrying only what the view needs
    req = types.SimpleNamespace()
    req.matchdict = {"company_id": company_id}
    req.response = DummyResponse()
    # Allow passing None or dict to simulate missing/invalid bodies
    req.json_body = body
    return req


class FakeRepo:
    def __init__(self, company_id="co-1", name="Acme Corp"):
        self._company = types.SimpleNamespace(company_id=company_id, name=name)

    def get(self, company_id):
        # Return a company object for any id
        return self._company


class FakeTaskManager:
    def __init__(self):
        self.calls = []

    def create_task(self, task_type, args: dict) -> str:
        # Record each call; the test will assert on args
        self.calls.append((task_type, args))
        return "fake-task-id"


@pytest.mark.parametrize(
    "body,expected",
    [
        (None, {"force_levels": False, "force_contacts": False}),
        ({}, {"force_levels": False, "force_contacts": False}),
        ({"force_levels": True}, {"force_levels": True, "force_contacts": False}),
        ({"force_contacts": True}, {"force_levels": False, "force_contacts": True}),
        (
            {"force_levels": True, "force_contacts": True},
            {"force_levels": True, "force_contacts": True},
        ),
        # Invalid types should default both to False (tolerant parsing)
        ({"force_levels": "yes", "force_contacts": "no"}, {"force_levels": False, "force_contacts": False}),
    ],
)
@pytest.mark.xfail(reason="Not implemented yet: research endpoint must accept flags and enqueue them")
def test_research_endpoint_enqueues_force_flags(monkeypatch, body, expected):
    # Arrange: patch repository and task manager
    fake_repo = FakeRepo()
    fake_tm = FakeTaskManager()

    monkeypatch.setattr(app_module, "models", types.SimpleNamespace(company_repository=lambda: fake_repo))
    monkeypatch.setattr(app_module, "tasks", types.SimpleNamespace(
        task_manager=lambda: fake_tm,
        TaskStatus=types.SimpleNamespace(PENDING=types.SimpleNamespace(value="pending")),
        TaskType=types.SimpleNamespace(COMPANY_RESEARCH="company_research"),
    ))

    req = make_request("co-1", body)

    # Act
    result = app_module.research_company(req)

    # Assert: endpoint returns a task id and pending status
    assert result["task_id"] == "fake-task-id"
    assert result["status"] == "pending"

    # Assert: flags are present in task args with expected boolean values
    assert len(fake_tm.calls) == 1
    _task_type, args = fake_tm.calls[0]
    # Existing required fields should still be present
    assert args.get("company_id") == "co-1"
    assert args.get("company_name") == "Acme Corp"
    # New flags should be included and correctly defaulted
    assert args.get("force_levels", None) == expected["force_levels"]
    assert args.get("force_contacts", None) == expected["force_contacts"]
