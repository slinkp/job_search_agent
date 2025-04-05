# Implementation Plan: Manual Company Research by URL

## 1. Backend Changes

### a. Modify Research Daemon
- [x] Modify `do_research` to handle receiving a URL and/or a name in addition to or instead of existing args
- [x] Reuse existing research code from `research_company`
- [x] Handle errors and create minimal company record if research fails
- [x] Add tests for the updated functionality

### b. Add new endpoint
- [x] Add `/api/companies` POST endpoint to create/research a (possibly new, possibly known) company
  - [x] args can be company URL or company name
- [x] Add route in `server/app.py`
- [x] Add request validation for URL
- [x] Return research task ID and status
- [x] Add unit tests for new endpoint
- [x] Add tests for URL validation
- [x] Add tests for error handling

### c. Backend Tests
- [x] Add unit test for new endpoint. This will go in a new file. Use pytest
- [x] Add tests for URL validation
- [x] Add tests for error handling
- [x] Add/modify tests for changes to research_daemon
- [x] Add/modify tests for any other changed backend code

## 2. Frontend Changes

### a. Add UI Components
- [x] Add "Research a company" button at top of company list
- [x] Create modal dialog for entering company URL and/or name
- [x] Add form validation for URL input
- [x] Add loading state and error handling
- [x] Add success feedback
- [ ] Add tests for UI components
- [ ] Add tests for form validation
- [ ] Add tests for error states

### b. Add API Integration
- [x] Add method to call new endpoint
- [x] Add task polling for company creation
- [x] Update company list on success
- [x] Handle errors and show feedback
- [ ] Add tests for API integration
- [ ] Add tests for task polling
- [ ] Add tests for error handling

### c. Frontend Tests
- [ ] Bootstrap testing of frontend
  - [ ] Give me pros and cons of modern frontend testing approaches
- [ ] Add tests for URL validation
- [ ] Add tests for error handling
- [ ] Add tests for UI components

## Implementation Notes

- Reuse existing code:
  - Use `TavilyRAGResearchAgent` for company research
  - Use `CompanyRepository` for database operations
  - Use existing task management system
  - Use existing company model and validation
  - If suggesting more new code, look for opportunities to change/reuse existing code first.

- Maintain existing patterns:
  - Use async/await for API calls
  - Use task-based processing for long operations
  - Use existing error handling patterns
  - Use existing UI patterns and components
  - Use existing backend data models