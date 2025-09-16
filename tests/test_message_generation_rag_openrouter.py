import message_generation_rag as rag_mod
from message_generation_rag import RecruitmentRAG
from langchain_openai import OpenAIEmbeddings


class DummyRetriever:
    def invoke(self, _input):
        return "DUMMY_CONTEXT"


class DummyLLM:
    def invoke(self, _input):
        return "LLM_REPLY"


def test_rag_uses_client_factory_with_openrouter(monkeypatch):
    captured = {}

    def fake_get_chat_client(provider, model, temperature, timeout):
        captured["provider"] = provider
        captured["model"] = model
        captured["temperature"] = temperature
        captured["timeout"] = timeout
        return DummyLLM()

    # Patch the factory referenced inside the module
    monkeypatch.setattr(rag_mod, "get_chat_client", fake_get_chat_client)

    messages = [("subj", "recruiter body", "my reply")]
    rag = RecruitmentRAG(messages)

    # Bypass vectorstore/embeddings setup to avoid DB/files and network
    rag.retriever = DummyRetriever()

    # Embeddings class should remain unchanged
    assert isinstance(rag.embeddings, OpenAIEmbeddings)

    rag.setup_chain(llm_type="gpt-5-mini", provider="openrouter")

    # Verify factory call
    assert captured["provider"] == "openrouter"
    assert captured["model"] == "gpt-5-mini"
    assert captured["temperature"] == 0.2
    assert captured["timeout"] == 120

    # The chain returns the DummyLLM output
    out = rag.generate_reply("hello")
    assert out == "LLM_REPLY"
