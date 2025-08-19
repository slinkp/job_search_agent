# Feature plan: Frontend test strategy and cleanup

## Plan: Improve frontend tests for Daily Message Dashboard

### Ground rules and definition of done
[ ] Follow feature-development-process.mdc; ≤2–3 files per step; ≤100 LOC where practical; keep tests fast and meaningful; run via ./test.
[ ] Acceptance criteria:
[ ] Utility logic (filtering, sorting, URL state, headings) covered by pure unit tests
[ ] Real component tests validate key user flows without asserting brittle template internals
[ ] Remove duplicate/brittle tests; align with current filterMode/sort API
[ ] Task/email services have minimal contract tests with fetch/timer control

### Extract pure utilities from daily-dashboard.js
[ ] Create server/static/dashboard-utils.js exporting:
[ ] filterMessages(messages, filterMode)
[ ] sortMessages(messages, newestFirst)
[ ] parseUrlState(search) → { filterMode, sortNewestFirst }
[ ] buildUpdatedSearch(search, { filterMode, sortNewestFirst })
[ ] getFilterHeading(filterMode, count)
[ ] Keep daily-dashboard.js delegating to these helpers
[ ] Tests: server/frontend/tests/dashboard-utils.test.js as above

### Real component tests (Alpine, mounted)
[ ] Add server/frontend/tests/daily-dashboard.component.test.js:
[ ] Mount real DOM via setupDocumentWithIndexHtml(document)
[ ] Import Alpine + daily-dashboard.js, dispatch alpine:init, Alpine.start()
[ ] Mock /api/messages and assert:
[ ] Filter buttons update heading and URL (filterMode)
[ ] Sort button toggles text and URL (sort)
[ ] Expand/collapse behavior on long messages
[ ] Use @testing-library/dom queries by text/role; add minimal data-testid only if needed

### Service tests (thin)
[ ] server/frontend/tests/task-polling.service.test.js: poll loop with fake timers; status text mapping
[ ] server/frontend/tests/email-scanning.service.test.js: status text/class; polling completes → triggers refresh hook (mock)

### Refactor/trim existing tests
[ ] Remove duplicated suites and outdated URL-state logic in daily-dashboard.test.js
[ ] Convert template-innerHTML assertions in daily-dashboard-integration.test.js into user-visible behavior assertions (or delete if redundant with component tests)
[ ] Stop using _x_dataStack directly; prefer DOM interactions

### Optional e2e (future)
[ ] Consider 1–2 Playwright flows (generate reply → poll → UI update; send & archive disabled/enabled states) when backend is stable. Do not auto-start server (manual step).

### Coverage and CI signals
[ ] Ensure coverage includes server/static/*.js but excludes HTML and setup
[ ] Keep tests deterministic with fake timers and controlled fetch mocks

### Cleanup
[ ] Remove/rename old test files to avoid confusion; update docs
[ ] Keep a tiny smoke test to catch catastrophic template load issues