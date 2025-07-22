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
- [ ] Check if there is duplicate functionality between app.js and daily-driver.js
- [ ] Factor those out

### 2.3 Implement buttons on daily dashboard page

These are not wired up.
Make sure not to duplicate code that already does the same job for the companies dashboard. Refactor as needed so both pages can use the same code where applicable.

- [ ] Research
- [ ] Generate Reply
- [ ] Archive


### 2.5 Manual workarounds and enhancements
- [x] Allow expanding the entire message body in the dashboard view
- [ ] Allow manually overriding the company name
  - [ ] This should search for existing companies with some fuzziness
  - [ ] adds the message to company.messages in the backend

### 3. Implement Batch Selection for efficiency
- [ ] Add checkbox column to message list
- [ ] Add "Select All" / "Select None" functionality
- [ ] Add selection counter ("X selected")
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

### 5. Add Status Summary
- [ ] Create status summary component showing:
  - [ ] "X unprocessed" (messages not replied to or archived)
  - [ ] "Y researched" (companies that have been researched)
  - [ ] "Z replied" (messages that have been replied to)
- [ ] Update summary in real-time as actions are performed
- [ ] Add visual indicators (colors, icons) for different statuses
- [ ] Add tests for status summary calculations

### 6. Backend Enhancements
- [ ] Add endpoint for getting unprocessed messages list
- [ ] Add batch research endpoint
- [ ] Add batch archive endpoint  
- [ ] Add batch reply generation endpoint
- [ ] Add status summary endpoint
- [ ] Add proper error handling for batch operations
- [ ] Add tests for all new endpoints

### 7. Polish and Integration
- [ ] Add link(s) from a company on the companies page to all associated emails on the email dashboard, and vice versa
  - [ ] I don't think we have real permalinks to companies or messages. We should
- [ ] Add confirmation dialogs for batch operations
- [ ] Ensure proper error handling and user feedback
- [ ] Add loading states for batch operations
- [ ] Add ability to toggle between daily dashboard and full company view
- [ ] Update navigation to highlight daily dashboard as primary view
- [ ] Add tests for error scenarios and edge cases

### 8. Documentation and Testing
- [ ] Update README with daily dashboard usage instructions
- [ ] Add comprehensive tests for batch operations
- [ ] Test with real recruiter message data
- [ ] Ensure all tests pass before marking complete
- [ ] Document any discovered issues or limitations

### 9. Enhanced UI Features (Future Iteration)
- [ ] On email view, add link to original message in gmail
- [ ] On the companies view, list all messages for the company.
  - [ ] Group them by normalized sender name and/or thread
- [ ] Add filter for "unprocessed messages" (messages that haven't been replied to or 
archived)
- [ ] Add advanced filtering and search within daily dashboard
- [ ] Add undo functionality for batch operations?
- [ ] Add batch editing of replies before sending?
- [ ] Add export functionality for daily reports?
- [ ] Add keyboard shortcuts for common actions

### MISC BUGS

- [ ] If research fails to find a name, but the company is already assigned a name, do NOT replace the existing name with generated placeholder

## Technical Implementation Notes

### Data Model Requirements
- RecruiterMessage model already exists with all required fields (sender, subject, date)
- Company model has status tracking for research/reply/archive states
- Need to define "unprocessed" clearly: messages where company is not replied to or archived

### API Design
- GET /api/unprocessed-messages - Returns list of unprocessed recruiter messages
- POST /api/batch-research - Start research for multiple companies
- POST /api/batch-archive - Archive multiple messages  
- POST /api/batch-reply - Generate replies for multiple messages
- GET /api/status-summary - Get counts for dashboard summary

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
