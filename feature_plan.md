# Feature Plan: Support OpenRouter models (gpt-5, gpt-5-mini) — Issue #68

Purpose
- Add first-class support for OpenRouter chat models (especially gpt-5 and gpt-5-mini) via a provider flag and OPENROUTER_API_KEY env var.
- Maintain existing behavior for OpenAI and Anthropic providers.
- Exclude company_classifier/ per issue note.

Scope
- Backend only.
- New provider value: openrouter.
- Update these components:
  - LLM client creation centralization (new ai/client_factory)
  - libjobsearch argument parsing and propagation
  - message_generation_rag (RAG reply generation)
  - company_researcher (company research agent)
  - Sweep any other direct ChatOpenAI/ChatAnthropic instantiations in backend (excluding company_classifier/)
- Add unit tests with mocks. No network calls.

Non-goals
- Do not change embeddings provider (keep text-embedding-3-large via OpenAIEmbeddings).
- No streaming/tool use/JSON mode enhancements in this issue.
- No frontend changes.

Success Criteria
- With provider=openrouter and model=gpt-5 or gpt-5-mini:
  - System constructs an OpenRouter-backed chat client using OPENROUTER_API_KEY and base_url=https://openrouter.ai/api/v1.
  - End-to-end flows that exercise RAG reply generation and company researcher work (with mocks).
  - All tests pass. No regressions for openai/anthropic providers.
- Clear error message if OPENROUTER_API_KEY missing when provider=openrouter.

Assumptions
- LangChain ChatOpenAI supports base_url and api_key override for OpenRouter route.
- OPENROUTER_API_KEY provided in environment (direnv friendly).
- We can thread provider/model through existing args/config without breaking tests.

Plan of Work
Single-task focus: I will implement exactly one checkbox at a time and nothing else. After each sub-task or nested sub-task, I will stop for approval and run ./test.

1) Centralize LLM client creation
- [x] Create ai/client_factory.py
  - [x] Implement get_chat_client(provider: Literal["openai","anthropic","openrouter"], model: str, temperature: float, timeout: int) -> BaseChatModel
  - [x] openai: return ChatOpenAI(model=model, temperature=..., timeout=...)
  - [x] anthropic: return ChatAnthropic(model=model, temperature=..., timeout=...)
  - [x] openrouter: return ChatOpenAI(model=model, temperature=..., timeout=..., base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"]) with clear error if key missing
  - [x] Do not handle embeddings here; keep them unchanged elsewhere
- [x] Tests: tests/test_client_factory.py
  - [x] Asserts provider=openrouter uses base_url and OPENROUTER_API_KEY (mock ChatOpenAI)
  - [x] Missing OPENROUTER_API_KEY raises helpful error
  - [x] openai/anthropic paths unchanged
- Stop for approval.

2) Update libjobsearch argument parsing and config propagation
- [x] Add --provider with choices ["openai","anthropic","openrouter"]; default remains current behavior (openai or existing SONNET_LATEST behavior)
- [x] If provider=openrouter and model not explicitly set, default model to gpt-5-mini
- [x] Thread provider through JobSearch -> EmailResponseGenerator -> RecruitmentRAG setup and into company_researcher main path
- [x] Tests: tests/test_libjobsearch_args.py
  - [x] Parses provider/model combos correctly
  - [x] Defaults apply (openrouter -> gpt-5-mini) if model not set
- Stop for approval.

3) Integrate in message_generation_rag.py
- [x] Replace direct ChatOpenAI/ChatAnthropic init in setup_chain with ai/client_factory.get_chat_client(provider, model, TEMPERATURE, TIMEOUT)
- [x] Keep embeddings creation as-is
- [x] Tests: tests/test_message_generation_rag_openrouter.py
  - [x] With provider=openrouter, ensure factory is called and returns the OpenRouter client (mocked)
  - [x] Embeddings remain OpenAIEmbeddings
- Stop for approval.

4) Integrate in company_researcher.py
- [x] In TavilyRAGResearchAgent.__init__, replace direct llm init with factory usage when llm not provided
- [x] In main() model selection paths, use factory for both OpenAI and Anthropic; add openrouter case
- [x] Tests: tests/test_company_researcher_openrouter.py
  - [x] With provider=openrouter, factory used and OpenRouter client selected (mocked)
- Stop for approval.

5) Sweep remaining backend LLM usages (exclude company_classifier/)
- [x] Grep for ChatOpenAI/ChatAnthropic in backend; migrate any remaining call sites to client_factory
- [x] Tests as needed to cover provider routing in those paths
- Stop for approval.

6) Error handling, logging, docs
- [x] Early validation and clear error if provider=openrouter and OPENROUTER_API_KEY missing
- [ ] Log provider/model (without secrets) at INFO on client creation
- [ ] Documentation: add a short note in README or docs/ about OPENROUTER_API_KEY and examples
- Stop for approval.

7) QA and rollout
- [ ] Ensure ./black-flake8-mypy . passes
- [ ] Run full ./test with OPENROUTER_API_KEY set (mock network)
- [ ] Manual smoke test (dev): provider=openrouter, model=gpt-5-mini; run flows that use RAG generation and researcher; no email sending
- [ ] Backout plan: switch provider to openai/anthropic; revert client_factory usage if necessary

Deliverables
- ai/client_factory.py with unit tests
- Updated libjobsearch arg parsing and propagation with tests
- message_generation_rag and company_researcher integrations with tests
- Minimal doc note for env var and usage
- All linters and tests passing

Open Questions
- Do we want to set OpenRouter-specific headers (HTTP-Referer, X-Title) now or later?
- Any other OpenRouter models to bless by default besides gpt-5 and gpt-5-mini?
- Should base_url be overrideable via env for future flexibility?

Risks and Mitigations
- Divergent code paths using different clients
  - Centralize creation in client_factory; write tests
- Missing env var causes runtime errors
  - Early validation and unit tests
- Changing embeddings inadvertently
  - Explicitly avoid changes; tests assert embeddings class unchanged

Notes
- Keep company_classifier/ out of scope.
- No frontend changes.
- Changes limited to a small number of backend files per step.

Feature process! Prrt!
