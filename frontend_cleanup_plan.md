# Feature plan: Frontend test strategy and cleanup

## Plan: Improve frontend tests for Daily Message Dashboard

### Ground rules and definition of done
[x] Follow feature-development-process.mdc; ≤2–3 files per step; ≤100 LOC where practical; keep tests fast and meaningful; run via ./test.
[ ] Acceptance criteria:
[x] Utility logic (filtering, sorting, URL state, headings) covered by pure unit tests
[ ] Real component tests validate key user flows without asserting brittle template internals
[ ] Remove duplicate/brittle tests; align with current filterMode/sort API
[ ] Task/email services have minimal contract tests with fetch/timer control

### Extract pure utilities from daily-dashboard.js
[x] Create server/static/dashboard-utils.js exporting:
[x] filterMessages(messages, filterMode)
[x] sortMessages(messages, newestFirst)
[x] parseUrlState(search) → { filterMode, sortNewestFirst }
[x] buildUpdatedSearch(search, { filterMode, sortNewestFirst })
[x] getFilterHeading(filterMode, count)
[x] Keep daily-dashboard.js delegating to these helpers
[x] Tests: server/frontend/tests/dashboard-utils.test.js as above

### Real component tests (Alpine, mounted)
[x] Attempted real Alpine-mounted test in `server/frontend/tests/daily-dashboard.component.test.js`
[x] Mounted DOM via `setupDocumentWithIndexHtml(document)`; imported Alpine and `daily-dashboard.js`
[x] Tried MutationObserver stubs and consolidated flow
[x] Decision: remove the real Alpine-mounted test for now due to jsdom/happy-dom instability (timeouts, OOM, plugin warnings). Coverage is already provided by:
    - `server/frontend/tests/daily-dashboard-integration.test.js` (DOM structure/wiring, user-visible behavior)
    - `server/frontend/tests/daily-dashboard.test.js` (state, URL persistence, local UI state)
    - `server/frontend/tests/dashboard-utils.test.js` (pure utility logic)
[x] Action taken: deleted `server/frontend/tests/daily-dashboard.component.test.js` to keep suite deterministic and fast
[ ] Future: consider 1–2 Playwright flows for true mount-level coverage once backend is stable (see Optional e2e)

### Tooling

[ ] Set up coverage reports for JS tests. Something that gives experience on par with python coverage
[ ] Enable js coverage in `./test`

### Service tests (thin)
[ ] server/frontend/tests/task-polling.service.test.js: poll loop with fake timers; status text mapping
[ ] server/frontend/tests/email-scanning.service.test.js: status text/class; polling completes → triggers refresh hook (mock)

### Refactor/trim existing tests
[x] Remove duplicated suites and outdated URL-state logic in daily-dashboard.test.js
[ ] Convert template-innerHTML assertions in daily-dashboard-integration.test.js into user-visible behavior assertions (or delete if redundant with component tests)
[ ] Stop using _x_dataStack directly; prefer DOM interactions

### Optional e2e (future)
[ ] Consider 1–2 Playwright flows (generate reply → poll → UI update; send & archive disabled/enabled states) when backend is stable. Do not auto-start server (manual step).

### Coverage and CI signals
[x] Ensure coverage includes server/static/*.js but excludes HTML and setup
[ ] Keep tests deterministic with fake timers and controlled fetch mocks

### Cleanup
[x] Remove/rename old test files to avoid confusion; update docs
[ ] Keep a tiny smoke test to catch catastrophic template load issues