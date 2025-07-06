# Daily Dashboard with Batch Processing Implementation Plan

This plan outlines the steps needed to implement a daily dashboard focused on processing unprocessed recruiter messages with batch operations, as specified in Week 1 Task 1 of the README.

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

## Implementation Steps

### 1. Create Daily Dashboard View
- [ ] Add new "Daily Dashboard" mode to toggle between current view and new message-centric view
- [ ] Create new UI component for unprocessed message list:
  - [ ] Show sender, subject, date for each unprocessed message
  - [ ] Display company name if extracted/researched
  - [ ] Show processing status (unprocessed, researched, replied, archived)
  - [ ] Add checkboxes for batch selection
- [ ] Add filter for "unprocessed messages" (messages that haven't been replied to or archived)
- [ ] Add tests for new UI components

### 2. Implement Batch Selection
- [ ] Add checkbox column to message list
- [ ] Add "Select All" / "Select None" functionality
- [ ] Add selection counter ("X selected")
- [ ] Track selected messages in frontend state
- [ ] Add visual feedback for selected items
- [ ] Add tests for selection functionality

### 3. Implement Batch Actions
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

### 4. Add Status Summary
- [ ] Create status summary component showing:
  - [ ] "X unprocessed" (messages not replied to or archived)
  - [ ] "Y researched" (companies that have been researched)
  - [ ] "Z replied" (messages that have been replied to)
- [ ] Update summary in real-time as actions are performed
- [ ] Add visual indicators (colors, icons) for different statuses
- [ ] Add tests for status summary calculations

### 5. Backend Enhancements
- [ ] Add endpoint for getting unprocessed messages list
- [ ] Add batch research endpoint
- [ ] Add batch archive endpoint  
- [ ] Add batch reply generation endpoint
- [ ] Add status summary endpoint
- [ ] Add proper error handling for batch operations
- [ ] Add tests for all new endpoints

### 6. Polish and Integration
- [ ] Add keyboard shortcuts for common actions
- [ ] Add confirmation dialogs for batch operations
- [ ] Ensure proper error handling and user feedback
- [ ] Add loading states for batch operations
- [ ] Add ability to toggle between daily dashboard and full company view
- [ ] Update navigation to highlight daily dashboard as primary view
- [ ] Add tests for error scenarios and edge cases

### 7. Documentation and Testing
- [ ] Update README with daily dashboard usage instructions
- [ ] Add comprehensive tests for batch operations
- [ ] Test with real recruiter message data
- [ ] Ensure all tests pass before marking complete
- [ ] Document any discovered issues or limitations

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