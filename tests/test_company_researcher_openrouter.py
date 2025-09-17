import datetime

import company_researcher as cr_mod
from models import CompaniesSheetRow


class DummyLLM:
    def __init__(self):
        self.name = "dummy-llm"

    def invoke(self, prompt):
        return type("Resp", (), {"content": "{}"})


class DummyAgent:
    def __init__(self, *, verbose=False, llm=None):
        self.llm = llm

    def main(self, *, url="", message=""):
        # Return a minimal CompaniesSheetRow similar to production path
        return CompaniesSheetRow(
            url=url,
            updated=datetime.date.today(),
            current_state="10. consider applying",
        )

    def get_discovered_alternate_names(self):
        return []


def test_company_researcher_uses_openrouter_factory(monkeypatch):
    captured = {}

    def fake_get_chat_client(provider, model, temperature, timeout):
        captured["provider"] = provider
        captured["model"] = model
        captured["temperature"] = temperature
        captured["timeout"] = timeout
        return DummyLLM()

    # Patch factory
    monkeypatch.setattr(cr_mod, "get_chat_client", fake_get_chat_client)
    # Patch agent to avoid network calls
    monkeypatch.setattr(cr_mod, "TavilyRAGResearchAgent", DummyAgent)

    row, discovered = cr_mod.main(
        url_or_message="some recruiter message",
        model="gpt-5-mini",
        is_url=False,
        provider="openrouter",
    )

    assert isinstance(row, CompaniesSheetRow)
    assert discovered == []

    # Verify factory invocation
    assert captured["provider"] == "openrouter"
    assert captured["model"] == "gpt-5-mini"
    assert captured["temperature"] == 0.7
    assert captured["timeout"] == 120
