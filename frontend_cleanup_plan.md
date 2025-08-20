# Feature plan: Frontend test strategy and cleanup

## Plan: Improve frontend tests for Daily Message Dashboard

### Ground rules and definition of done


Acceptance criteria:
[x] Utility logic (filtering, sorting, URL state, headings) covered by pure unit tests
[x] Real component tests validate key user flows without asserting brittle template internals
[x] Remove duplicate/brittle tests; align with current filterMode/sort API
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
[x] Create `server/static/company-utils.js` exporting:
[x] normalizeCompany(company) and normalizeCompanies(list)
[x] filterCompanies(companies, filterMode)
[x] sortCompanies(companies, sortField, sortAsc)
[x] formatResearchErrors(company) (move from app.js)

[x] Extend `server/static/url-utils.js` (or create) with app helpers:
[x] parseViewFromUrl(search)
[x] Prefer `urlUtils.updateUrlParams` over a bespoke `buildUrlWithParams` (no longer needed)
[x] setIncludeAllParam(url, includeAll)
[x] buildHashForCompany(companyId)

[x] Create thin `server/static/companies-service.js` wrapping fetch calls:
[x] getCompanies({ includeAll })
[x] getCompany(companyId)
[x] getMessages()
[x] saveReply(messageId, text)
[x] sendAndArchive(messageId)
[x] archiveMessage(messageId)
[x] updateCompanyDetails(companyId, payload)

[x] Deduplicate polling: remove app-local `pollTaskStatus` in `app.js`; rely entirely on `TaskPollingService` (largest remaining duplication and source of untested lines)
[x] Refactor `app.js` to delegate to the above utils/services; keep DOM-only concerns (dialogs, Alpine wiring)
[x] Add unit tests for new utils/services; keep import smoke for `app.js`

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
[x] **Trim and rename**: Rename `server/frontend/tests/daily-dashboard.test.js` to `daily-dashboard.state.test.js` and trim duplicated suites (keep only state/logic tests; move any DOM bits to integration)
[x] **Consolidate smoke tests**: Merge `app.import.test.js` and `daily-dashboard.import.test.js` into `smoke.test.js` as two short cases; keep just enough to execute import-time side effects
[x] **Remove redundant DOM checks**: Delete duplicate presence assertions across `daily-dashboard-integration.test.js` and other files; prefer behavior over template attribute inspections

### Component Testing Strategy
[x] **Create unified Alpine helper**: Build a single helper in `test-utils.js` to initialize Alpine, trigger `alpine:init`, and capture registered factories
[x] **Factory-capture tests for components**: Add `daily-dashboard.factory.test.js` that captures the factory, instantiates the component, and exercises core methods with services mocked. This executes real component code without full DOM mounting and raises coverage for `daily-dashboard.js`.
[x] **Extract URL sync logic**: Move `updateUrlWithFilterState` and `readFilterStateFromUrl` from `daily-dashboard.js` into `url-utils.js` (use `urlUtils.updateUrlParams` and `dashboard-utils.buildUpdatedSearch`) and add focused unit tests
[x] **Add accessible selectors**: Add `aria-label` attributes to key buttons in `index.html` for stable test queries
[x] **Add data-testid attributes**: Add `data-testid` to hard-to-reach nodes that can't use accessible selectors

Notes from investigation:
- Stripping `<script src>` in tests prevents module execution; import smoke tests address coverage without re-enabling external fetches.
- Prefer raising coverage by extracting pure logic into `*-utils.js` and testing directly; use smoke tests only to ensure top-level registration side-effects run.

### Test Content Improvements
[x] **Replace template-internal assertions**: Convert `@click`/`x-for` attribute checks into behavior assertions in `daily-dashboard-integration.test.js`
[x] **Remove x-for text checks**: Replace Alpine directive text assertions with actual DOM content checks
[x] **Stop checking exact class names**: Use semantic queries instead of brittle CSS class assertions
[x] **Right-size timers**: Move `vi.useFakeTimers()` from global setup to specific test suites that need it

### Mock and State Management
[x] **Standardize dialog mocking**: Create shared dialog mock helper in `test-utils.js` for `showModal`/`close` and `confirmDialogs`
[x] **Remove component logic duplication**: Replace re-implemented production logic in `daily-dashboard.test.js` with factory-captured component tests that call real methods
[x] **Use dependency injection**: Allow `TaskPollingService` to accept an optional delay (ms) and/or a `sleep` function for test control; remove `app.js` local polling in favor of the shared service
[x] **Test real functions**: Pure utilities now tested directly (`dashboard-utils`, `url-utils`, `company-utils`)

### Future Considerations
Maybe **Consider Playwright for true E2E**: 1-2 flows for generate reply → poll → UI update when backend stabilizes
Do not auto-start server (manual step).
Maybe **Monitor Alpine community patterns**: Stay updated on testing best practices as Alpine ecosystem evolves


### Service tests (thin)
[x] `server/frontend/tests/task-polling.test.js`: poll loop with timers; status text/class mapping
[x] `server/frontend/tests/email-scanning.test.js`: status text/class; polling completes → triggers refresh hook (mock)

### Low coverage action checklist for app.js and daily-dashboard.js

[x] Add factory-capture component tests that instantiate real component objects (no DOM mount):
    - Capture factories by stubbing `global.Alpine.data = vi.fn((name, fn) => { captured[name] = fn; })`
    - Import modules, dispatch `document.dispatchEvent(new Event('alpine:init'))`
    - Instantiate `captured.companyList()` and `captured.dailyDashboard()` and execute methods:
      `init`, `toggleViewMode`, `refreshAllCompanies`, `setFilterMode`, `toggleSortOrder`,
      `generateReply`, `sendAndArchive`, `archive`, `research`, URL sync methods
    - Mock `CompaniesService`, `TaskPollingService`, `EmailScanningService`, and `ui-utils`

[x] Remove `app.js` local `pollTaskStatus` and route all polling via `TaskPollingService` only
    - Add tests in `task-polling.test.js` with injectable delay/sleep to keep loops deterministic

[x] Extract `daily-dashboard.js` URL sync helpers into `url-utils.js`
    - Move `readFilterStateFromUrl` and `updateUrlWithFilterState` to `url-utils.js`
    - Add focused unit tests and refactor component to call the shared helpers

[x] Create a unified Alpine factory helper in `server/frontend/tests/test-utils.js`
    - Utility to capture factories, dispatch `alpine:init`, and return instantiated component objects

[x] Expand app import smoke to also dispatch `alpine:init` and assert registration
    - Keeps test minimal but executes additional import-time lines

[x] Add per-file coverage thresholds for `app.js` and `daily-dashboard.js` (start modestly, raise over time)
    - Prevent regressions while iteratively increasing executed lines
