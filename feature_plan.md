Plan: Show Unsent Replies Inline in Daily Message Dashboard (Issue #7)

We will enable viewing, editing, regenerating, and sending unsent (generated) replies directly in the Daily Message Dashboard with a message-centric frontend and API. For now, the backend will continue storing the draft reply on the company (`Company.reply_message`) as a compatibility layer. This keeps the dashboard future-proof while deferring data model refactors.

0. Ground rules and definition of done

- [ ] Follow `feature-development-process.mdc` strictly; keep changes ≤2–3 files per step and ≤100 LOC where possible; add tests before/with code; all tests must pass via `./test`.
- [ ] Acceptance criteria:
  - [ ] Generated (unsent) replies surface inline with each message row
  - [ ] Edit, regenerate, save, send, archive actions available in the dashboard
  - [ ] Clear reply status shown: none, generated, sent

1. Backend API: message-centric endpoints backed by company-level storage (temporary)

- [ ] Do NOT change the DB schema for now; keep draft storage in `Company.reply_message`
- [x] `GET /api/messages`: include `reply_message` for each message derived from its company; add `reply_status` derived as:
  - [x] `sent` if `message.reply_sent_at` is set
  - [x] `generated` if `company.reply_message` is non-empty and `message.reply_sent_at` is not set
  - [x] `none` otherwise
- [x] `POST /api/messages/{message_id}/reply`: generate a reply and store it in the associated company’s `reply_message`; reuse existing task/polling.
- [x] `PUT /api/messages/{message_id}/reply`: update the associated company’s `reply_message` with user edits; return an updated company/message payload as needed.
- [x] Tests: endpoint payload shape for `GET /api/messages`; generate/update flows update the company-level draft and reflect in subsequent GETs

2. Frontend: render reply preview/editor inline (message-centric)

- [ ] Under each message row, show a reply block:
  - [ ] When `reply_status === 'generated'`, show collapsed preview; expandable to full; provide Edit
  - [ ] Edit opens textarea; re-use the same edit code and UX we have on the companies page. Save calls `PUT /api/messages/{id}/reply`
  - [ ] When `reply_status === 'none'`, show Generate Reply button (`POST /api/messages/{id}/reply`)
  - [ ] When `reply_status === 'sent'`, show Sent badge; hide editing actions
- [ ] Show status badges (Generated, Sent, Archived) alongside existing fields
- [ ] Preserve existing filtering/sorting/expansion; no company-centric assumptions in the UI
- [ ] Tests: unit tests for conditional rendering and local state; integration test for expand/collapse with replies

3. Frontend: generation/edit/save flow bound to message_id

- [ ] Use `message_id` in `generatingMessages` and related UI state
- [ ] Generate → poll → populate from `reply_message`; Regenerate replaces the draft (with confirmation)
- [ ] Save edits via `PUT /api/messages/{id}/reply` and update preview on success
- [ ] Tests: state transitions for generate → edit → save; regenerate flow

4. Send & Archive with implicit save (message-centric trigger, company-backed)

- [ ] Wire Send & Archive button to a message-level action; on the server, implicitly save the current draft to the company first, then send and archive the message
- [ ] Disable during send; on success mark message `sent` and reflect archive state; hide editing actions
- [ ] Tests: backend for send-and-archive semantics via `message_id`; frontend integration to verify save-then-send

5. Error handling, edge cases, and UX polish

- [ ] Archived or sent messages render as non-editable; actions hidden/disabled
- [ ] API failures show toasts; user edits remain in textarea
- [ ] Multiple messages per company: for now, we assume one active reply per company; dashboard remains message-centric, but edits/generation effectively target the company draft; document this in UI copy/tooltip
- [ ] Unknown company on a message: show with `company_name = "Unknown Company"`; disable reply editing/generation
- [ ] Tests: edge cases (no draft + sent, archived, unknown company)

6. Test inventory and coverage

- [ ] Backend tests: `GET /api/messages` payload (includes `reply_message`, `reply_status`), `POST/PUT /api/messages/{id}/reply` map to company draft, optional `send_and_archive` behavior
- [ ] Frontend unit: conditional rendering, loading states, state transitions per `message_id`
- [ ] Frontend integration: end-to-end dashboard flows (generate → edit → save; regenerate confirmation; send & archive with implicit save)

7. Cleanup and deprecation (future work, not in this feature)

- [ ] Optional: `POST /api/messages/{message_id}/send_and_archive` maps to existing company-centric send/archive flow but keyed by `message_id`
- [ ] Migrate backend from `Company.reply_message` to per-message drafts
- [ ] Migrate reply generation task and task polling response to be message-centric, not company-centric. Probably do this by making a new task type and deprecating the old one.
- [ ] Update company view to be message-centric throughout
- [ ] Remove legacy company-level draft usage once migration is complete
- [ ] Update README/docs accordingly

Notes

- This feature keeps the dashboard and API message-centric while using `Company.reply_message` under the hood temporarily. Later, we can migrate storage to per-message drafts without changing the dashboard UX.