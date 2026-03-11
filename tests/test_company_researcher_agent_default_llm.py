import company_researcher as cr_mod
from constants import GPT_MINI_LATEST


class DummyLLM:
    def invoke(self, prompt):
        return type("Resp", (), {"content": "{}"})


def test_agent_default_llm_uses_factory(monkeypatch):
    captured = {}

    def fake_get_chat_client(provider, model, temperature, timeout):
        captured.update(
            dict(provider=provider, model=model, temperature=temperature, timeout=timeout)
        )
        return DummyLLM()

    monkeypatch.setattr(cr_mod, "get_chat_client", fake_get_chat_client)

    agent = cr_mod.TavilyRAGResearchAgent(verbose=False, llm=None)
    # Ensure factory was used with the default openai/gpt-4 combo
    assert captured["provider"] == "openai"
    assert captured["model"] == GPT_MINI_LATEST
    assert captured["temperature"] == 0.7
    assert captured["timeout"] == 120
    # Sanity: the agent uses the returned dummy LLM
    assert isinstance(agent.llm, DummyLLM)
