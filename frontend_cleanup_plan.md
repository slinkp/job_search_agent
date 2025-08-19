# Feature plan: Frontend test strategy and cleanup

## Plan: Improve frontend tests for Daily Message Dashboard

### Ground rules and definition of done
[x] Follow feature-development-process.mdc; ≤2–3 files per step; ≤100 LOC where practical; keep tests fast and meaningful; run via ./test.

Acceptance criteria:
[x] Utility logic (filtering, sorting, URL state, headings) covered by pure unit tests
[ ] Real component tests validate key user flows without asserting brittle template internals
[ ] Remove duplicate/brittle tests; align with current filterMode/sort API
[ ] Task/email services have minimal contract tests with fetch/timer control
    - Note: Added minimal real (unmocked) smoke for `CompanyResearchService` to raise coverage

### Extract pure utilities from daily-dashboard.js
[x] Create server/static/dashboard-utils.js exporting:
[x] filterMessages(messages, filterMode)
[x] sortMessages(messages, newestFirst)
[x] parseUrlState(search) → { filterMode, sortNewestFirst }
[x] buildUpdatedSearch(search, { filterMode, sortNewestFirst })
[x] getFilterHeading(filterMode, count)
[x] Keep daily-dashboard.js delegating to these helpers
[x] Tests: server/frontend/tests/dashboard-utils.test.js as above

### Extract pure utilities from app.js
[ ] Create `server/static/company-utils.js` exporting:
[ ] normalizeCompany(company) and normalizeCompanies(list)
[ ] filterCompanies(companies, filterMode)
[ ] sortCompanies(companies, sortField, sortAsc)
[ ] formatResearchErrors(company) (move from app.js)

[ ] Extend `server/static/url-utils.js` (or create) with app helpers:
[ ] parseViewFromUrl(search)
[ ] buildUrlWithParams(currentUrl, params)
[ ] setIncludeAllParam(url, includeAll)
[ ] buildHashForCompany(companyId)

[ ] Create thin `server/static/companies-service.js` wrapping fetch calls:
[ ] getCompanies({ includeAll })
[ ] getCompany(companyId)
[ ] getMessages()
[ ] saveReply(messageId, text)
[ ] sendAndArchive(messageId)
[ ] archiveMessage(messageId)
[ ] updateCompanyDetails(companyId, payload)

[ ] Deduplicate polling: remove app-local pollTaskStatus; rely on `TaskPollingService`
[ ] Refactor `app.js` to delegate to the above utils/services; keep DOM-only concerns (dialogs, Alpine wiring)
[ ] Add unit tests for new utils/services; keep import smoke for `app.js`

### Real component tests (Alpine, mounted)
[x] Attempted real Alpine-mounted test in `server/frontend/tests/daily-dashboard.component.test.js`
[x] Mounted DOM via `setupDocumentWithIndexHtml(document)`; imported Alpine and `daily-dashboard.js`
[x] Tried MutationObserver stubs and consolidated flow
[x] Decision: remove the real Alpine-mounted test for now due to jsdom/happy-dom instability (timeouts, OOM, plugin warnings). Coverage is already provided by:
    - `server/frontend/tests/daily-dashboard-integration.test.js` (DOM structure/wiring, user-visible behavior)
    - `server/frontend/tests/daily-dashboard.test.js` (state, URL persistence, local UI state)
    - `server/frontend/tests/dashboard-utils.test.js` (pure utility logic)
[x] Action taken: deleted `server/frontend/tests/daily-dashboard.component.test.js` to keep suite deterministic and fast


### Tooling

[x] Set up coverage reports for JS tests. Something that gives experience on par with python coverage
[x] Enable js coverage in `./test`


### Refactor/trim existing tests
[x] Remove duplicated suites and outdated URL-state logic in daily-dashboard.test.js
[x] Convert template-innerHTML assertions in daily-dashboard-integration.test.js into user-visible behavior assertions (or delete if redundant with component tests)
[x] Stop using _x_dataStack directly; prefer DOM interactions

### Coverage and CI signals
[x] Ensure coverage includes server/static/*.js but excludes HTML and setup
[x] Keep tests deterministic with fake timers and controlled fetch mocks

### Cleanup
[x] Remove/rename old test files to avoid confusion; update docs
[x] Keep a tiny smoke test to catch catastrophic template load issues

### Coverage improvements (smoke)
[x] Identify 0% coverage root causes: stripped `<script src>` in tests and full module mocks prevent execution
[x] Add import smoke test for `server/static/app.js` to execute top-level side-effects (style injection) safely
[x] Add import smoke test for `server/static/daily-dashboard.js` and trigger `alpine:init` to register component
[x] Add thin real service smoke test for `server/static/company-research.js` (without vi.mock), stubbing `fetch`
[x] Verify coverage now non-zero for previously 0% files via `./test --no-python`

## Current Issues Identified

### Environment and Configuration Issues
[x] **Fix DOM environment mismatch**: Change vitest.config.js to use `environment: "happy-dom"` and remove manual Window injection from vitest.setup.js
[x] **Increase test timeouts**: Update vitest.config.js timeouts from 1000ms to 5000ms for test/hook timeouts
[x] **Centralize fetch mocking**: Add `vi.stubGlobal('fetch', vi.fn())` to vitest.setup.js and `vi.restoreAllMocks()` to afterEach

### Test Structure and Organization
[ ] **Split daily-dashboard.test.js**: Create separate files for state management, reply expansion, and URL persistence tests
[ ] **Consolidate smoke tests**: Merge smoke.test.js checks into a single minimal integration test file
[ ] **Remove redundant DOM checks**: Delete duplicate presence assertions across daily-dashboard-integration.test.js and other files

### Component Testing Strategy
[ ] **Create unified Alpine helper**: Build single helper in test-utils.js that loads HTML, imports Alpine, starts it, provides stable selectors
[ ] **Extract URL sync logic**: Move `updateUrlWithFilterState` and `readFilterStateFromUrl` from daily-dashboard.js into url-utils.js module
[ ] **Add accessible selectors**: Add `aria-label` attributes to key buttons in index.html for stable test queries
[ ] **Add data-testid attributes**: Add `data-testid` to hard-to-reach nodes that can't use accessible selectors

Notes from investigation:
- Stripping `<script src>` in tests prevents module execution; import smoke tests address coverage without re-enabling external fetches.
- Prefer raising coverage by extracting pure logic into `*-utils.js` and testing directly; use smoke tests only to ensure top-level registration side-effects run.

### Test Content Improvements
[ ] **Replace template-internal assertions**: Convert @click attribute checks to behavior assertions in daily-dashboard-integration.test.js
[ ] **Remove x-for text checks**: Replace Alpine directive text assertions with actual DOM content checks
[ ] **Stop checking exact class names**: Use semantic queries instead of brittle CSS class assertions
[x] **Right-size timers**: Move `vi.useFakeTimers()` from global setup to specific test suites that need it

### Mock and State Management
[ ] **Standardize dialog mocking**: Create shared dialog mock helper in test-utils.js for showModal/close
[ ] **Remove component logic duplication**: Delete re-implemented production logic from test mocks in daily-dashboard.test.js
[ ] **Use dependency injection**: Refactor polling services to accept injectable delays for test control
[ ] **Test real functions**: Replace mock implementations with calls to actual utility functions

### Future Considerations
[ ] **Consider Playwright for true E2E**: 1-2 flows for generate reply → poll → UI update when backend stabilizes
Do not auto-start server (manual step).
[ ] **Monitor Alpine community patterns**: Stay updated on testing best practices as Alpine ecosystem evolves
[ ] **Document testing patterns**: Create guide for team on when to use unit vs integration vs E2E tests


### Service tests (thin)
[ ] server/frontend/tests/task-polling.service.test.js: poll loop with fake timers; status text mapping
[ ] server/frontend/tests/email-scanning.service.test.js: status text/class; polling completes → triggers refresh hook (mock)
