import pytest
import types
import libjobsearch
import email_client


class _TestDummyRAG:
    def generate_reply(self, msg: str) -> str:
        return ""


class _FakeGmailRepliesSearcher:
    def authenticate(self):
        pass

    def get_my_replies_to_recruiters(self, max_results: int):
        return []

    def get_new_recruiter_messages(self, max_results: int):
        return []

    def send_reply(self, thread_id: str, message_id: str, reply: str) -> bool:
        # Tests may patch the GmailRepliesSearcher with autospec; provide the full
        # interface expected by the test suite so autospec'ed mocks include these methods.
        return True

    def label_and_archive_message(self, message_id: str) -> bool:
        return True


@pytest.fixture(autouse=True)
def _patch_email_and_rag(monkeypatch):
    # Avoid real Gmail during tests
    monkeypatch.setattr(email_client, "GmailRepliesSearcher", _FakeGmailRepliesSearcher)
    # Avoid building a real RAG in tests; provide a minimal stub with generate_reply
    monkeypatch.setattr(
        libjobsearch.EmailResponseGenerator,
        "_build_reply_rag",
        lambda self, old_replies: _TestDummyRAG(),
    )
    yield
