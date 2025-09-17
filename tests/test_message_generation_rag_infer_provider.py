import message_generation_rag as rag_mod
from message_generation_rag import RecruitmentRAG


class DummyRetriever:
    def invoke(self, _input):
        return "CTX"


class DummyLLM:
    def invoke(self, _input):
        return "OK"


def test_rag_infers_openai_when_llm_type_openai(monkeypatch):
    captured = {}

    def fake_get_chat_client(provider, model, temperature, timeout):
        captured.update(
            dict(provider=provider, model=model, temperature=temperature, timeout=timeout)
        )
        return DummyLLM()

    monkeypatch.setattr(rag_mod, "get_chat_client", fake_get_chat_client)
    rag = RecruitmentRAG([("s", "m", "r")])
    rag.retriever = DummyRetriever()

    rag.setup_chain(llm_type="openai", provider=None)

    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o"
    assert captured["temperature"] == 0.2
    assert captured["timeout"] == 120
    assert rag.generate_reply("x") == "OK"


def test_rag_infers_anthropic_when_llm_type_claude(monkeypatch):
    captured = {}

    def fake_get_chat_client(provider, model, temperature, timeout):
        captured.update(
            dict(provider=provider, model=model, temperature=temperature, timeout=timeout)
        )
        return DummyLLM()

    monkeypatch.setattr(rag_mod, "get_chat_client", fake_get_chat_client)
    rag = RecruitmentRAG([("s", "m", "r")])
    rag.retriever = DummyRetriever()

    rag.setup_chain(llm_type="claude", provider=None)

    assert captured["provider"] == "anthropic"
    assert captured["model"] == "claude-3-5-sonnet-20240620"
    assert rag.generate_reply("x") == "OK"
