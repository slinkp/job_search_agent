I cannot run CLI commands (gh, ./test, sqlite3) or access files outside what you've added to the chat.
Please provide the following so I can reproduce and fix issue #63:

1) Issue content
- Run locally and paste the full output of:
  gh issue view 63 --comments

2) Current test results
- Run locally and paste the full output of:
  ./test

3) Add these frontend files (copy their full contents into the chat). I will need them to run/author frontend tests and to reason about failing tests:
- server/static/url-utils.js
- server/static/daily-dashboard.js
- server/static/app.js
- server/static/task-polling.js
- server/static/companies-service.js
- server/static/company-utils.js
- server/static/ui-utils.js
- server/frontend/tests/url-utils.test.js
- server/frontend/tests/daily-dashboard.state.test.js
- server/frontend/tests/daily-dashboard-integration.test.js
- server/frontend/tests/app.factory.test.js

4) Optional DB inspection (if the issue seems data-related)
- Run and paste outputs of:
  sqlite3 data/companies.db 'pragma integrity_check;'
  sqlite3 data/companies.db '.schema'
  sqlite3 -header -csv data/companies.db 'SELECT company_id,name,deleted_at FROM companies LIMIT 10;'
  sqlite3 -header -csv data/companies.db 'SELECT id,company_id,alias,normalized_alias,is_active FROM company_aliases LIMIT 10;'
  sqlite3 -header -csv data/companies.db 'SELECT id,company_id,event_type,timestamp FROM events ORDER BY timestamp DESC LIMIT 10;'

What I'll do once you provide the above:
- Write/adjust a failing test that reproduces #63.
- Propose minimal SEARCH/REPLACE edits to the code to fix it, explaining each change in a few sentences.
- Ensure tests pass (you'll run them locally) and provide a commit message including "closes #63".

Notes:
- If you want me to modify additional files that are not yet in the chat, list their full paths or add them here. Per repository rules I cannot edit files I don't have the exact current contents for.
- After you paste the gh/test outputs and add the frontend files, reply "go ahead" and I will produce precise SEARCH/REPLACE blocks for edits and new/updated tests.
