# Daily Dashboard with Batch Processing Implementation Plan

This plan outlines the steps needed to implement a daily dashboard focused on processing unprocessed recruiter messages with batch operations, as specified in Week 1 Task 1 of the README.

## CRITICAL PROCESS NOTE

Follow all rules in @feature-development-process.mdc strictly,
and all other applicable rules at all times.

## Primary Goals
1. Create a message-centric daily workflow for processing unprocessed recruiter messages
2. Enable batch operations to efficiently handle multiple messages at once
3. Provide clear status summaries to track daily progress
4. Maintain focus on unprocessed items while allowing access to full company management

## Current State Analysis

### What Exists
- **Company-centric dashboard** - Shows all companies with filtering/sorting capabilities
- **Individual email scanning** - "Scan Emails" button processes recruiter messages one by one
- **Individual actions** - Research, generate reply, send/archive for each company individually
- **Status tracking** - Research status, reply status, archived status per company
- **Recruiter message data** - Full RecruiterMessage model with sender, subject, date, email thread links
- **Backend endpoints** - Complete API for individual company operations and email scanning

### What's Missing for Task 1
- **Message-centric view** - Current view shows companies, but Task 1 requires showing unprocessed recruiter messages (sender, subject, date)
- **Batch selection** - No way to select multiple messages/companies for batch operations
- **Batch actions** - No "Research selected", "Archive selected", "Reply to selected" functionality
- **Status summary** - No "X unprocessed, Y researched, Z replied" summary display
- **Unprocessed focus** - Current view shows all companies, but Task 1 wants focus on unprocessed messages
- **Complete research decoupling** - Currently `research=false` only skips 2nd stage research, still does 1st stage
- **Full message fetching** - Currently fetches only 10 messages, should fetch all new messages by default

## Implementation Steps

### 0. Implement simple heuristic for company fit
- [x] Hardcoded rules based on my preferences

### 1. Create Daily Dashboard View
- [x] Add new "Daily Dashboard" mode to toggle between current company-centric view and new message-centric view
- [x] Create new UI component for unprocessed message list:
  - [x] Show sender, subject, date for each unprocessed message
  - [x] Display company name if extracted/researched
  - [x] Show processing status (unprocessed, researched, replied, archived)
- [x] Add tests for new UI components

### 2. Decouple Research from Message Fetching (IMMEDIATE PRIORITY)
- [x] **Fully decouple research from message fetching**: Currently `research=false` only skips the 2nd stage of research, but still does the 1st stage. Need to make research completely optional.
- [x] **Fetch all Gmail messages by default**: Change from fetching only 10 messages to fetching all messages we don't already have.
- [x] **Implement/verify message deduplication**: Ensure "we already have this message" logic works correctly:
  - [x] Check how message deduplication is currently determined
  - [x] Verify it works reliably (by message ID, thread ID, or other unique identifier)
  - [x] Implement proper deduplication if not already working
  - [x] Add tests for deduplication logic
- [x] **Update email scanning API**: Modify `/api/scan_recruiter_emails` to:
  - [x] Accept null for `max_messages` to mean unlimited messages
  - [x] Accept `do_research` parameter (default: false) for complete research decoupling
  - [x] Handle large message fetches efficiently. Check gmail docs and consider batching?
- [x] **Update frontend**: Modify daily dashboard to:
  - [x] Remove `max_messages` parameter from scan button
  - [x] Add option to enable/disable research during scan
  - [x] Show progress for large message fetches
- [x] **Add tests** for new email scanning behavior


### 2.1 Refactor for DRY
- [x] Check if there is duplicate functionality between app.js and daily-driver.js
- [x] Factor those out
  - [x] Extract EmailScanningService for shared email scanning functionality
  - [x] Extract ui-utils.js for shared UI utility functions
  - [x] Extract TaskPollingService for shared task polling functionality

### 2.3 Implement buttons on daily dashboard page

These are not wired up.
Make sure not to duplicate code that already does the same job for the companies dashboard. Refactor as needed so both pages can use the same code where applicable.

- [x] Research
- [x] Generate Reply
- [x] Archive
  - [x] Add to dashboard page
  - [x] Fix archive backend to take an optional message ID.
        If passed, archive that specific message, not just the default company message
  - [x] Change frontend to send message ID
  - [x] Update research daemon and task handlers to support message_id as an arg to ignore and archive
  - [x] Add backend endpoint `/messages/<message_id>/archive`.
        POST to that should do the same as we currently do when message id is passed to the existing method.
  - [x] Update daily js to use the new endpoint by message id
  - [x] Update app.js to use the new endpoint by message id
- [x] Clean up backend: 
   - [x] Check if anything in frontend or back end still using archive(company)
   - [x] remove API endpoint for archive(company)
   - [x] remove company_id support from archive feature everywhere else
  

### 2.4 Message-centric API refactor



- [x] POST   /api/messages/{message_id}/reply to generate, PUT /api/messages/{message_id}/reply to manually update
  - [x] Add new endpoint `/api/messages/{message_id}/reply` for generating replies by message_id
  - [x] Add comprehensive tests for the new endpoint
  - [x] Add new endpoint `/api/messages/{message_id}/reply` for updating replies by message_id (PUT)
  - [x] Add comprehensive tests for the update endpoint
  - [x] Update frontend to use these instead of "/api/companies/{company_id}/reply_message"
  - [x] Remove "/api/companies/{company_id}/reply_message"

- [ ] GET    /api/messages   # List all messages
  - [ ] Update dashboard to use this instead of /api/companies


- [ ] QUESTION: Pause here and think about: Do we really need
      send + archive to be atomic? It's probably not in the models anyway.
      Could we wait for the send to succeed and then do an archive?
      Maybe not because it's all done async

- [ ] POST /api/messages/{message_id}/send_and_archive  # Send reply and archive message
  - [ ] Update frontend to use these instead of "/api/companies/{company_id}/send_and_archive"
  - [ ] Remove the old method

- [ ] refactor frontend to make `isGeneratingMessage(company)` work with message id instead

### 2.5 Manual workarounds and enhancements
- [x] Allow expanding the entire message body in the dashboard view
- [ ] Allow manually overriding the company name on a message:
  - [ ] Add a concept of "alternate names" to the backend data model
  - [ ] Add a concept of "verified name" to the backend data model
  - [ ] Anytime research finds a new name, add the new one as an alternate name
  - [ ] Manually setting name should check for existing company with any of the known alternates
  - [ ] Manually setting the name adds the message to company.messages in the backend
  - [ ] Manually setting the name sets the new one as "verified name"

### 2.7 Add Status Summary
- [ ] Create status summary component showing:
  - [ ] "X unprocessed" (messages not replied to or archived)
  - [ ] "Y researched" (companies that have been researched)
  - [ ] "Z replied" (messages that have been replied to)
- [ ] Update summary in real-time as actions are performed
- [ ] Add visual indicators (colors, icons) for different statuses
- [ ] Add tests for status summary calculations


### 3. Implement Batch Selection for efficiency
- [ ] Add checkbox column to message list
- [ ] Add "Select All" / "Select None" functionality
- [ ] Track selected messages in frontend state
- [ ] Add visual feedback for selected items
- [ ] Add tests for selection functionality

### 4. Implement Batch Actions
- [ ] Add "Research Selected" batch action:
  - [ ] Backend endpoint to start research for multiple companies
  - [ ] Progress tracking for batch research operations
  - [ ] Handle partial failures gracefully
- [ ] Add "Archive Selected" batch action:
  - [ ] Backend endpoint to archive multiple messages without replies
  - [ ] Update status tracking for archived messages
- [ ] Add "Reply to Selected" batch action:
  - [ ] Generate replies for all selected messages
  - [ ] Allow batch review and editing before sending
  - [ ] Send and archive multiple messages
- [ ] Add tests for all batch operations


### 6. Backend Enhancements
- [ ] Add or update existing messages endpoint to get unprocessed messages
- [ ] Add status summary endpoint
- [ ] Add proper error handling for batch operations

### 7. Polish and Integration
- [ ] Add link(s) from a company on the companies page to all associated emails on the email dashboard, and vice versa
  - [ ] I don't think we have real permalinks to companies or messages. We should!
- [ ] Add confirmation dialogs for batch operations
- [ ] Ensure proper error handling and user feedback
- [ ] Add loading states for batch operations
- [ ] Start with daily dashboard as default view
- [ ] Add tests for untested error scenarios and edge cases

### 8. Documentation and Testing
- [ ] Coverage reports of frontend tests?
- [ ] Add comprehensive tests for batch operations
- [ ] Manual test with real recruiter message data
- [ ] Ensure all tests pass before marking complete
- [ ] Document any discovered issues or limitations

### 9. Enhanced UI Features (Future Iteration)
- [ ] On email view, add link to original message in gmail
- [ ] On the companies view, list all messages for the company.
  - [ ] Group them by normalized sender name and/or thread
- [ ] Add filter for "unprocessed messages" (messages that haven't been replied to or 
archived)
- [ ] Add advanced filtering and search within daily dashboard
- [ ] Add batch editing of replies before sending?

### 10. API refactorings deferred:

- [ ] GET  /api/messages?filter=unprocessed   # List all unprocessed messages
  - [ ] Can probably defer until we are doing filters

- [ ] GET  /api/messages/{message_id}  # Get specific message details
  - [ ] Defer this until we have a definite use case where we don't have the message already eg via company.message
  - [ ] Update frontend to use this instead of company.message

### 11. Data Model Refactoring (Future)

- [ ] **Company Archiving Refactoring**: Make company archiving a computed property based on message status
  - [ ] Remove `company.status.archived_at` database field
  - [ ] Add computed property `company.is_archived` that returns true only when ALL messages are archived
  - [ ] Update frontend filtering to use individual message `archived_at` instead of company-level
  - [ ] Update UI displays to use computed property
  - [ ] Migration: Add computed property alongside existing field, update frontend, then remove database field
  - [ ] **Rationale**: Companies should only be "archived" when all their messages are archived. This creates cleaner separation between message-level operations and company-level aggregations, and properly supports multi-message companies.

### MISC BUGS AND ENHANCEMENTS

- [ ] If research fails to find a name, but the company is already assigned a name, do NOT replace the existing name with generated placeholder
- [ ] I have no idea if we're being consistent w timezones in the db. Should everything be UTC by default?

## Technical Implementation Notes

### Data Model Requirements
- RecruiterMessage model already exists with all required fields (sender, subject, date)
- Company model has status tracking for research/reply/archive states
- Need to define "unprocessed" clearly: messages where company is not replied to or archived

### Frontend Architecture
- Use existing Alpine.js setup with new daily dashboard component
- Maintain current company dashboard for full management view
- Add toggle between "Daily Dashboard" and "Company Management" modes
- Reuse existing styling and components where possible

## Success Criteria
- [ ] Daily dashboard shows unprocessed recruiter messages (sender, subject, date)
- [ ] Batch selection works for multiple messages
- [ ] "Research selected", "Archive selected", "Reply to selected" actions work
- [ ] Status summary shows "X unprocessed, Y researched, Z replied"
- [ ] All actions update the display in real-time
- [ ] Can toggle between daily dashboard and full company view
- [ ] **Email scanning fetches all new messages by default** (not just 10)
- [ ] **Research is completely decoupled from message fetching** (optional, not automatic)
- [ ] **Message deduplication works reliably** (no duplicate messages in database)
- [ ] All tests pass
- [ ] User can efficiently process multiple messages in a single session

## Deferred Features
These features would be valuable but are not required for the initial implementation:
- Keyboard shortcuts for power users
- Undo functionality for batch operations
- Advanced filtering and search within daily dashboard
- Integration with calendar for daily goals
- Batch editing of replies before sending
- Export functionality for daily reports 


