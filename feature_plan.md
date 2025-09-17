Issue: https://github.com/slinkp/job_search_agent/issues/72

Title: Force salary/levels and/or contacts research from UI (Companies + Messages dashboards)

1) Problem Statement
- The app conditionally runs parts of research:
  - Contacts (LinkedIn) follow-up runs only when is_good_fit(...) is true.
  - Levels/salary research is skipped for placeholder company names.
- Users need an explicit override to force either or both actions from:
  - Companies view (per company)
  - Messages dashboard (per message)

2) Goals and Non-Goals
- Goals
  - Add per-action flags to override gates:
    - force_levels: run levels and compensation even if name is a placeholder.
    - force_contacts: run LinkedIn contacts even if not a good fit.
  - Wire flags end-to-end: UI → frontend service → API → task args → daemon → libjobsearch.
  - Backward compatible: no change when flags are absent/false.
- Non-Goals
  - Changing the is_good_fit heuristic.
  - Persisting “always force” preferences.
  - Broad UI redesign.

3) Acceptance Criteria
- Companies view:
  - Two checkboxes “Force Salary” and “Force Contacts” appear next to the Research button on each company card.
  - Clicking Research sends the selected flags for that company and kicks off research.
- Messages dashboard:
  - Two checkboxes “Force Salary” and “Force Contacts” appear next to the Research button on each message card.
  - Clicking Research sends the selected flags for that message’s company.
- Backend:
  - POST /api/companies/{company_id}/research accepts optional JSON with force_levels, force_contacts (both default false).
  - Task args carry these flags; daemon passes them to libjobsearch.JobSearch.research_company.
  - libjobsearch respects flags:
    - followup (contacts) runs when force_contacts is true, regardless of fit.
    - levels/compensation run even for placeholder names when force_levels is true.
- All existing tests pass; new tests cover flag propagation and behavior.

4) High-Level Approach
- UI: Add ephemeral checkbox state per card (company._forceLevels/_forceContacts and message._forceLevels/_forceContacts) rendered near existing Research buttons.
- Service: Extend CompaniesService.research(companyId, options={}) to POST JSON body with force_levels/force_contacts (default false).
- API: server/app.py research_company() parses optional JSON body and injects flags into task args.
- Daemon: research_daemon.py.do_research reads flags from args and forwards to JobSearch.research_company(..., force_levels, force_contacts).
- Core: libjobsearch.JobSearch.research_company signature gains force flags. Update:
  - followup gate: if force_contacts or is_good_fit(row).
  - research_levels/research_compensation accept force parameter to bypass placeholder-name early-return when force_levels is true.
  - Pass force into both methods from research_company.

5) Detailed Plan (by layer)
- Frontend
  - server/static/index.html
    - Companies view: add two checkboxes inside each company card’s .research-status before the Research button.
    - Messages view: add the same inside each message card’s .research-section before the Research button.
  - server/static/app.js
    - In research(company), call companiesService.research(company.company_id, { force_levels: !!company._forceLevels, force_contacts: !!company._forceContacts }).
  - server/static/daily-dashboard.js
    - In research(message), call companiesService.research(message.company_id, { force_levels: !!message._forceLevels, force_contacts: !!message._forceContacts }).
  - server/static/companies-service.js
    - research(companyId, options = {}) issues POST with headers Content-Type: application/json and body { force_levels: !!options.force_levels, force_contacts: !!options.force_contacts }.
  - Tests (Vitest)
    - server/frontend/tests/app.factory.test.js: mock CompaniesService.research and assert it is called; add a case to ensure options propagate when set.
    - server/frontend/tests/daily-dashboard-integration.test.js: extend to toggle new checkboxes and verify CompaniesService.research called with expected payload (or verify fetch body if mocking directly). Ensure existing DOM assertions still pass (we’re only adding inputs).

- Backend
  - server/app.py
    - research_company: safely parse request.json_body (default {}), extract boolean flags with default False, include in task args for TaskType.COMPANY_RESEARCH.
  - research_daemon.py
    - do_research: read flags from args (default False) and pass to jobsearch.research_company(..., force_levels, force_contacts).
  - libjobsearch.py
    - JobSearch.research_company(..., do_advanced=True, force_levels=False, force_contacts=False):
      - Call research_levels(row, force=force_levels).
      - Call research_compensation(row, force=force_levels).
      - Change followup gate: if force_contacts or self.is_good_fit(row): followup_research_company(row).
    - research_levels(row, force=False): when force is True, skip the placeholder-name early-return.
    - research_compensation(row, force=False): same as above.
    - Add info logs indicating forced override usage for observability.
  - tasks.py
    - No changes needed (task args accept arbitrary JSON).
  - models.py
    - No schema changes; optional: include “forced=true” annotation in RESEARCH_COMPLETED/RESEARCH_ERROR event details for auditability.
  - Tests (pytest)
    - server/app research endpoint: flags parsed and injected into task args (mock task_manager()).
    - research_daemon.do_research: forwards flags to JobSearch (mock research_company and assert call).
    - JobSearch.research_company unit tests:
      - With force_contacts=True and is_good_fit=False, followup executes.
      - With force_levels=True and placeholder name, levels and compensation still run (assert no early-return and method invocation).

6) Constraints, Risks, Mitigations
- Constraint: Follow repo convention to not commit FE and BE in same PR.
  - Mitigation: Two PRs (backend first, then frontend).
- Risk: Confusion over “Force Salary” while levels/salary often run already.
  - Mitigation: Forcing explicitly bypasses placeholder-name skip; add tooltip copy clarifying that.
- Risk: JSON body absent/invalid.
  - Mitigation: Wrap parse; default flags to False.
- Risk: Cache keys for disk_cache may change when passing new kwargs.
  - Mitigation: Acceptable; cache miss is fine; no migration needed.

7) Observability
- Log flags at:
  - server/app when creating task.
  - research_daemon when reading args.
  - libjobsearch when forced steps are taken.
- Optional: add “forced=true” in event details for research events.

8) Manual verification:
- Start daemon and server, test all four combinations of flags on: a placeholder-name company, and a not-good-fit company.
- Confirm task status updates, logs, and no regressions in existing flows.

9) Testing Strategy
- Python
  - Unit tests for endpoint parsing, daemon forwarding, and libjobsearch gating logic with flags.
  - Ensure errors still roll up to task status FAILED and events logged as before.
- JavaScript
  - Unit tests for service payloads and component calls.
  - Integration in daily-dashboard: ensure checkboxes exist, wire up without breaking existing assertions (tests largely check presence; adding inputs is additive).
  - Run full ./test to verify both Py and JS suites.

10) Tasks Checklist
- Backend
  - [ ] server/app.py: parse flags and include in task args.
  - [ ] research_daemon.py: forward flags to JobSearch.research_company.
  - [ ] libjobsearch.py: add force flags, modify gates, add force param to levels/compensation, log overrides.
  - [ ] Tests for all of the above.
- Frontend
  - [ ] companies-service.js: research() sends JSON body with flags.
  - [ ] app.js: pass flags from company._forceLevels/_forceContacts.
  - [ ] daily-dashboard.js: pass flags from message._forceLevels/_forceContacts.
  - [ ] index.html: add checkboxes in both views near Research button.
  - [ ] Tests updated/added.

