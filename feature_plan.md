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
  - Add two override flags per action:
    - force_levels: run levels/compensation even if the name is a placeholder.
    - force_contacts: run LinkedIn contacts even if not a good fit.
  - Wire flags end-to-end: UI → frontend service → API → task → daemon → research core.
  - Preserve current defaults when flags are absent/false.
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

4) Linear Implementation Checklist (test-first; proceed strictly top-to-bottom)

- [x] Backend: API accepts override flags and enqueues them
  - [x] Write tests to assert POST /api/companies/{id}/research accepts JSON body with { force_levels, force_contacts } booleans defaulting to false, and that task args include these flags.
  - [x] Implement tolerant JSON parsing (default both flags to false when body missing/invalid), include flags in task creation, and add a concise log noting company_id and flags.
  - [x] Run tests and fix until green.

- [x] Backend: Task pipeline forwards flags to research
  - [x] Write tests to assert the research daemon reads flags from task args and calls JobSearch.research_company(..., force_levels, force_contacts).
  - [x] Implement flag extraction in the daemon and pass-through to the research entry point; keep behavior unchanged when flags are absent/false.
  - [x] Run tests and fix until green.

- [ ] Backend: Research core respects flags
  - [x] Write tests for JobSearch.research_company to verify:
    - [x] follow-up contacts runs when force_contacts=True even if is_good_fit(...) is false,
    - [x] levels/compensation run when force_levels=True even for placeholder names (bypass placeholder skip),
    - [x] existing behavior is preserved when both flags are False.
  - [x] Add optional force_levels and force_contacts params to the research entry point, use them to override gates, and add minimal info logs when forced.
  - [x] Run tests and fix until green.

- [ ] Frontend: Service can send flags with research request
  - [ ] Write a unit test that CompaniesService.research(companyId, options) POSTs JSON { force_levels, force_contacts } and remains backward compatible when options are omitted.
  - [ ] Implement options parameter, send JSON body, and default flags to false when not provided.
  - [ ] Run tests and fix until green.

- [ ] Frontend: Companies view shows override checkboxes and sends flags
  - [ ] Add two checkboxes next to the Research button on each company card: “Force Salary” and “Force Contacts” (ephemeral per-company state).
  - [ ] Update research(company) to pass { force_levels: !!company._forceLevels, force_contacts: !!company._forceContacts } to the service.
  - [ ] Add/adjust tests to verify the new inputs exist and that research() calls the service with the expected options.
  - [ ] Run tests and fix until green.

- [ ] Frontend: Messages dashboard shows override checkboxes and sends flags
  - [ ] Add two checkboxes next to the Research button on each message card: “Force Salary” and “Force Contacts” (ephemeral per-message state).
  - [ ] Update research(message) to pass { force_levels: !!message._forceLevels, force_contacts: !!message._forceContacts } to the service.
  - [ ] Add/adjust integration test to toggle the checkboxes and assert the service is called with the expected options.
  - [ ] Run tests and fix until green.

- [ ] Manual verification
  - [ ] Start the server and daemon; verify that researching with no flags behaves as before.
  - [ ] Verify each combination: salary only, contacts only, both; try on a placeholder-name company and a not-good-fit company.
  - [ ] Confirm task status updates and no obvious UI regressions.

