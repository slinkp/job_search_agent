Plan: Show Unsent Replies Inline in Daily Message Dashboard (Issue #7)

We will enable viewing, editing, regenerating, and sending unsent (generated) replies directly in the Daily Message Dashboard with a message-centric frontend and API. For now, the backend will continue storing the draft reply on the company (`Company.reply_message`) as a compatibility layer. This keeps the dashboard future-proof while deferring data model refactors.

0. Ground rules and definition of done

- [ ] Follow `feature-development-process.mdc` strictly; keep changes ≤2–3 files per step and ≤100 LOC where possible; add tests before/with code; all tests must pass via `./test`.
- [ ] Acceptance criteria:
  - [ ] Generated (unsent) replies surface inline with each message row
  - [ ] Edit, regenerate, save, send, archive actions available in the dashboard
  - [ ] Clear reply status shown: none, generated, sent

1. Backend API: message-centric endpoints backed by company-level storage (temporary)

- [x] Do NOT change the DB schema for now; keep draft storage in `Company.reply_message`
- [x] `GET /api/messages`: include `reply_message` for each message derived from its company; add `reply_status` derived as:
  - [x] `sent` if `message.reply_sent_at` is set
  - [x] `generated` if `company.reply_message` is non-empty and `message.reply_sent_at` is not set
  - [x] `none` otherwise
- [x] `POST /api/messages/{message_id}/reply`: generate a reply and store it in the associated company’s `reply_message`; reuse existing task/polling.
- [x] `PUT /api/messages/{message_id}/reply`: update the associated company’s `reply_message` with user edits; return an updated company/message payload as needed.
- [x] Tests: endpoint payload shape for `GET /api/messages`; generate/update flows update the company-level draft and reflect in subsequent GETs

1.5 Database backfill

- [x] Add a migration script to backfill `recruiter_messages.reply_sent_at`. Follow existing migration script format / pattern
- [x] For each message: iff `message.reply_sent_at` is not set: Look up the company; check if `company.status.reply_sent_at` is set. If so, set the message's `reply_sent_at` to the same value.  
- [x] Log if updated. Log total count of updates and total count of rows not updated

2. Frontend: render reply preview/editor inline (message-centric)

- [x] Under each message row, show a reply block:
  - [x] Show status badges (Generated, Sent, Archived) alongside existing fields
  - [x] When `reply_status === 'none'`, show Generate Reply button (don't worry about wiring it up yet); should be able to reuse code from companies edit flow;
        also Edit button (don't worry about wiring that either)
  - [x] Edit button opens textarea; re-use the same edit code and UX we have on the companies page, but refactor that code as needed to
        use message data model instead of company data model.
  - [x] Save button calls `PUT /api/messages/{id}/reply` and updates preview on success; should be able to reuse code from companies edit flow
  - [x] Generate button should send `POST /api/messages/{id}/reply`). Use `message_id` in `generatingMessages` and related UI state. Should be able to re-use code from companies flow, refactor as needed if it assumes company data model.
  - [x] Generate or Regenerate should trigger polling job, then when finished update state from the `reply_message` in the backend API. Should be able to re-use code from companies flow, refactor if needed.
  - [x] When `reply_status === 'generated'`, show collapsed preview; expandable to full; provide Edit and Regenerate buttons; should be able to re-use code from companies flow for this too
  - [x] When `reply_status === 'sent'`, show Sent badge; hide/disable editing actions, same as companies edit flow (i think it does this?)
- [x] Preserve existing filtering/sorting/expansion; no company-centric assumptions in the UI
- [x] Tests: unit tests for conditional rendering and local state; integration test for expand/collapse with replies
- [x] Tests: state transitions for generate → edit → save; regenerate flow

3. Send & Archive with implicit save (message-centric trigger, company-backed)

- [x] Wire Send & Archive button to a message-level action (keyed by message id); on the server, send message, then archive the message and mark company archived too
- [x] Frontend: implicitly call save of current draft text first. Then send_and_archive_message
- [ ] Do send async:
  - [x] Disable action buttons during send
  - [x] show spinner during send
  - [x]  alert when job done
  - [x]  on success mark message `sent` and reflect archive state;
  - [x]  for messages that are sent, disable edit and regenerate buttons
  - [x]  for messages that are archived, disable archive button
  - [x]  for messages that are archived, disable research button
  - [x]  Do all that on company page too
- [x] Tests: backend for send-and-archive semantics via `message_id`; frontend integration to verify save-then-send

4. Error handling, edge cases, and UX polish

- [x] Archived or sent messages render as non-editable; actions hidden/disabled
- [x] API failures show toasts; user edits remain in textarea
- [x] Multiple messages per company: for now, we assume one active reply per company; dashboard remains message-centric, but edits/generation effectively target the company draft
- [x] Tests: edge cases (no draft + sent, archived, unknown company)

5. Test inventory and coverage

- [ ] Frontend: think hard about what value the test strategy brings. Tests that simply exercise mocks aren't very useful; we have mocks that re-implement much of the behavior of the mocked code and that's a very bad smell. Can we do better?  Would it help to refactor some more of the code into functions that don't depend on alpine so we can do more simple unit testing of input/output ?
  - [ ] Also, look for redundancy between server/frontend/tests/daily-dashboard-integration.test.js and server/frontend/tests/daily-dashboard.test.js 
- [ ] Backend tests: `GET /api/messages` payload (includes `reply_message`, `reply_status`), `POST/PUT /api/messages/{id}/reply` map to company draft, optional `send_and_archive` behavior
- [ ] Frontend unit: conditional rendering, loading states, state transitions per `message_id`
- [ ] Frontend integration: end-to-end dashboard flows (generate → edit → save; regenerate confirmation; send & archive with implicit save)

6. Cleanup and deprecation (future work, not in this feature)

- [ ] Mark issue 7 as complete on github
- [ ] Migrate backend from `Company.reply_message` to per-message drafts
- [ ] Migrate reply generation task and task polling response to be message-centric, not company-centric. Probably do this by making a new task type and deprecating the old one.
- [ ] Remove message flow from company page? Don't really need same UX in two places?
- [ ] Remove legacy company-level draft usage once migration is complete
- [ ] Update README/docs if needed

Notes

- This feature keeps the dashboard and API message-centric while using `Company.reply_message` under the hood temporarily. Later, we can migrate storage to per-message drafts without changing the dashboard UX.