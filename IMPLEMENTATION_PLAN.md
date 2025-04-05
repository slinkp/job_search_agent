# Implementation Plan: Manual Company Research by URL

## 1. Backend Changes

### a. Modify Research Daemon
- Modify `do_research` to handle receiving a URL and/or a name in addition to
  or instead of existing args
- Reuse existing research code from `research_company`
- Handle errors and create minimal company record if research fails

### b. Add new endpoint
- Add `/api/companies` POST endpoint to create/research a (possibly new, possibly known) company
  - args can be company URL or company name
- Add route in `server/app.py`
- Add request validation for URL
- Return research task ID and status

## 2. Frontend Changes

### a. Add UI Components
- Add "Research a company" button at top of company list
- Create modal dialog for entering company URL and/or name
- Add form validation for URL input
- Add loading state and error handling
- Add success feedback

### b. Add API Integration
- Add method to call new endpoint
- Add task polling for company creation
- Update company list on success
- Handle errors and show feedback

## 3. Testing

### a. Backend Tests
- Add unit tests for new endpoint
- Add tests for URL validation
- Add tests for error handling

- Add/modify tests for changes to research_daemon
- Add/modify tests for any other changed backend code

### b. Frontend Tests
- Bootstrap testing of frontend
  - Give me pros and cons of modern frontend testing approaches
- Add tests for URL validation
- Add tests for error handling
- Add tests for UI components

## Implementation Notes

- Reuse existing code:
  - Use `TavilyRAGResearchAgent` for company research
  - Use `CompanyRepository` for database operations
  - Use existing task management system
  - Use existing company model and validation
  - If suggesting more new code, look for opportunities to change/reuse
    existing code first.

- Maintain existing patterns:
  - Use async/await for API calls
  - Use task-based processing for long operations
  - Use existing error handling patterns
  - Use existing UI patterns and components 
  - Use existing backend data models