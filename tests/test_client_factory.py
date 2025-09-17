import os

import pytest

from ai import client_factory


def test_openrouter_uses_base_url_and_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")
    created = {}

    class DummyChatOpenAI:
        def __init__(self, **kwargs):
            created["kwargs"] = kwargs

    monkeypatch.setattr(client_factory, "ChatOpenAI", DummyChatOpenAI)
    client_factory.get_chat_client("openrouter", "gpt-5-mini", 0.2, 60)

    assert created["kwargs"]["model"] == "gpt-5-mini"
    assert created["kwargs"]["temperature"] == 0.2
    assert created["kwargs"]["timeout"] == 60
    assert created["kwargs"]["base_url"] == "https://openrouter.ai/api/v1"
    assert created["kwargs"]["api_key"] == "sk-test-123"


def test_openrouter_missing_key_raises_helpful_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        client_factory.get_chat_client("openrouter", "gpt-5-mini", 0.1, 30)


def test_openai_path_calls_chat_openai(monkeypatch):
    created = {}

    class DummyChatOpenAI:
        def __init__(self, **kwargs):
            created["kwargs"] = kwargs

    monkeypatch.setattr(client_factory, "ChatOpenAI", DummyChatOpenAI)
    client_factory.get_chat_client("openai", "gpt-4o-mini", 0.3, 15)

    assert created["kwargs"]["model"] == "gpt-4o-mini"
    assert created["kwargs"]["temperature"] == 0.3
    assert created["kwargs"]["timeout"] == 15
    assert "base_url" not in created["kwargs"]
    assert "api_key" not in created["kwargs"]


def test_anthropic_path_calls_chat_anthropic(monkeypatch):
    created = {}

    class DummyChatAnthropic:
        def __init__(self, **kwargs):
            created["kwargs"] = kwargs

    monkeypatch.setattr(client_factory, "ChatAnthropic", DummyChatAnthropic)
    client_factory.get_chat_client("anthropic", "claude-sonnet", 0.1, 45)

    assert created["kwargs"]["model"] == "claude-sonnet"
    assert created["kwargs"]["temperature"] == 0.1
    assert created["kwargs"]["timeout"] == 45
