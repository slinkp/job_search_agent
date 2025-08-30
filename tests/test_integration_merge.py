import datetime
from unittest.mock import patch

import server.app
from models import Company, CompaniesSheetRow, Event, EventType, RecruiterMessage
from tests.test_companies_endpoint import clean_test_db


class DummyRequest:
    def __init__(self, json_body=None, matchdict=None):
        self.json_body = json_body or {}
        self.matchdict = matchdict or {}
        self.response = type("Resp", (), {"status": "200 OK"})()


def test_e2e_merge_flow_from_detection_to_completion(clean_test_db):
    repo = clean_test_db

    # Create a canonical and a duplicate with overlapping alias
    canon = Company(company_id="canon", name="Canon", details=CompaniesSheetRow(name="Canon"))
    dup = Company(company_id="dup", name="Cannon", details=CompaniesSheetRow(name="Cannon"))
    repo.create(canon)
    repo.create(dup)

    # Overlapping alias on duplicate
    repo.create_alias("dup", "Canon", source="manual")

    # Detection via API
    with patch("models.company_repository", return_value=repo):
        request = DummyRequest(matchdict={"company_id": "canon"})
        overlaps = server.app.get_potential_duplicates(request)

    assert overlaps == ["dup"], "Potential duplicates should include the duplicate company"

    # Merge task creation via API
    with patch("models.company_repository", return_value=repo), patch(
        "tasks.task_manager"
    ) as mock_tm:
        mock_tm.return_value.create_task.return_value = "task-merge-1"
        request = DummyRequest(json_body={"duplicate_company_id": "dup"}, matchdict={"company_id": "canon"})
        resp = server.app.merge_companies(request)
        assert resp["task_id"] == "task-merge-1"

    # Execute merge (simulate daemon completion)
    assert repo.merge_companies("canon", "dup") is True

    # Verify duplicate is soft-deleted and aliases migrated
    canon_aliases = {a["alias"] for a in repo.list_aliases("canon")}
    assert "Canon" in canon_aliases


def test_merge_data_integrity_post_merge(clean_test_db):
    repo = clean_test_db

    canonical = Company(
        company_id="canon",
        name="Canonical Corp",
        details=CompaniesSheetRow(name="Canonical Corp", type="Tech", url=""),
    )
    repo.create(canonical)

    duplicate = Company(
        company_id="dup",
        name="Canonical",
        details=CompaniesSheetRow(
            name="Canonical",
            type="",
            url="https://canonical.example.com",
            headquarters="NYC",
        ),
    )
    repo.create(duplicate)

    # Aliases and data bound to duplicate
    repo.create_alias("dup", "Canonical Corporation", "manual")
    msg = RecruiterMessage(
        message_id="m-1",
        company_id="dup",
        message="Hello",
        subject="Hi",
        thread_id="t-1",
        email_thread_link="https://mail/thread/t-1",
        date=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    )
    repo.create_recruiter_message(msg)
    repo.create_event(Event(company_id="dup", event_type=EventType.COMPANY_CREATED))

    # Perform merge
    assert repo.merge_companies("canon", "dup") is True

    # Integrity checks
    # 1) Duplicate is soft-deleted
    with repo._get_connection() as conn:  # type: ignore[attr-defined]
        row = conn.execute(
            "SELECT deleted_at FROM companies WHERE company_id = ?",
            ("dup",),
        ).fetchone()
        assert row is not None and row[0] is not None

    # 2) All messages point to canonical
    msgs = repo.get_recruiter_messages("canon")
    assert {m.message_id for m in msgs} == {"m-1"}

    # 3) Events point to canonical
    events = repo.get_events(company_id="canon")
    assert len(events) == 1

    # 4) No aliases left pointing at duplicate
    dup_aliases = repo.list_aliases("dup")
    assert dup_aliases == []

    # 5) Canonical details merged
    canon_after = repo.get("canon")
    assert canon_after is not None
    assert canon_after.details.type == "Tech"
    assert canon_after.details.url == "https://canonical.example.com"
    assert canon_after.details.headquarters == "NYC"


