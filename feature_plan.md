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

4) Linear Implementation Checklist (complete top-to-bottom; keep FE and BE in separate PRs)

- [ ] Backend PR: API accepts override flags
  - [ ] Update the research endpoint for a company to accept optional JSON body with force_levels and force_contacts (both default false).
  - [ ] Include these flags in the task args when creating the company research task.
  - [ ] Log a concise message that includes company_id and the flags used.

- [ ] Backend PR: Task pipeline forwards flags
  - [ ] Read force_levels and force_contacts from task args in the research daemon.
  - [ ] Pass both flags to the research entry point.
  - [ ] Keep behavior unchanged if flags are absent/false.

- [ ] Backend PR: Research core respects flags
  - [ ] Add optional force_levels and force_contacts params to the research entry point.
  - [ ] Ensure contacts follow-up runs when force_contacts is true, even if not a good fit.
  - [ ] Ensure levels/compensation run when force_levels is true, even for placeholder names.
  - [ ] Leave all defaults unchanged when flags are false.
  - [ ] Add minimal info logs when a forced override is used.

- [ ] Backend PR: Tests are green
  - [ ] Add unit tests for API flag parsing → task args.
  - [ ] Add a unit test that the daemon forwards flags to the research entry point.
  - [ ] Add unit tests that the research core overrides gates when flags are true and preserves behavior when false.
  - [ ] Run the full test suite and ensure no regressions.

- [ ] Frontend PR: Service can send flags
  - [ ] Extend the research(companyId, options={}) service method to POST a JSON body with force_levels and force_contacts (default false).
  - [ ] Keep the method backward compatible for callers that don’t pass options.

- [ ] Frontend PR: Companies view UI exposes flags
  - [ ] Add two checkboxes next to the Research button on each company card: “Force Salary” and “Force Contacts”.
  - [ ] Track state per company as ephemeral fields.
  - [ ] Pass the checkbox values to the service method when invoking research.

- [ ] Frontend PR: Messages dashboard UI exposes flags
  - [ ] Add the same two checkboxes next to the Research button on each message card.
  - [ ] Track state per message as ephemeral fields.
  - [ ] Pass the checkbox values to the service method when invoking research.

- [ ] Frontend PR: Tests are green
  - [ ] Add/update unit tests to verify the service sends the flags from checkbox state.
  - [ ] Add/update integration tests to ensure the new inputs exist and that calling Research uses the selected flags.
  - [ ] Run the full test suite and ensure no regressions.

- [ ] Rollout sequencing
  - [ ] Land the Backend PR first (API + daemon + research core + tests).
  - [ ] Land the Frontend PR second (UI + service + tests).
  - [ ] Avoid mixing frontend and backend changes in the same commit/PR.

- [ ] Manual verification
  - [ ] Start the server and daemon; verify that researching with no flags behaves as before.
  - [ ] Verify force_levels only; verify force_contacts only; verify both; on both a placeholder-name company and a not-good-fit company.
  - [ ] Confirm task status updates appear and no obvious UI regressions.

