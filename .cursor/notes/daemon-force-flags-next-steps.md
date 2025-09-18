I will implement exactly: Backend: Task pipeline forwards flags to research — Run tests and fix until green. And nothing else.

Summary of analysis
- I inspected research_daemon.do_research and libjobsearch.JobSearch.research_company.
- No code changes appear necessary: do_research extracts `force_levels` and `force_contacts` from task args, builds `research_kwargs` only when keys are present, and calls `self.jobsearch.research_company(..., **research_kwargs)`.
- JobSearch.research_company already accepts `force_levels` and `force_contacts` with defaults, so the current pass-through shape should be compatible with the tests.

What I need from you (next steps)
1. Run the full test suite: ./test --no-cover
2. If tests pass, reply here saying the tests are green and you'll check off the checklist item.
3. If any tests fail, paste the full failing test output / traceback here. If the failure is about unexpected kwargs or missing args in JobSearch.research_company, include that traceback exactly so I can make a minimal fix.

If a code change becomes necessary
- I will propose minimal SEARCH/REPLACE edits to the exact file(s) that need modification (no more than 2–3 files and ≤100 LOC unless you approve otherwise).
- I will say "I will implement exactly [checkbox/bullet] and nothing else." before making edits.
- I will include one SEARCH/REPLACE block per file edit and explain each change in a couple of sentences.
- After you apply the edits, re-run ./test --no-cover and paste back any remaining failures.

Notes
- I will not make any edits until you paste failing test output (if any) or confirm tests are green.
- If you want me to proceed to fix a specific failing trace immediately, paste it and I will propose minimal edits.

Feature process! Prrt!
