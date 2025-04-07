# Spreadsheet Import Feature Implementation Plan

## Overview
This plan outlines the steps needed to implement the feature to import companies from a spreadsheet into the application database, as specified in the README roadmap:

```
  - [ ] Support importing companies from spreadsheet
     - [ ] Add button to UX for this
     - [ ] Add a background task
     - [ ] It should use existing name normalization to check for duplicates
           in which case, merge the spreadsheet data into the db data and vice versa.
           (Spreadsheet data wins over DB data if both exist)
```

The implementation will follow a back-to-front approach, ensuring all tests pass after each step, and adding new tests as needed.

## Implementation Steps

### 1. Understand Existing Code Structure
- [x] Understand how companies are stored in the spreadsheet
- [x] Understand how companies are stored in the database
- [x] Understand how tasks are created and processed
- [x] Understand how name normalization works for finding duplicates

### 2. Create a New Task Type in the Backend
- [x] Add a new `IMPORT_COMPANIES_FROM_SPREADSHEET` task type to `TaskType` enum in `tasks.py`
- [x] Write tests to ensure the new task type is recognized by the system

### 3. Use Existing Spreadsheet Client for Data Retrieval
- [x] Review the existing `MainTabCompaniesClient` class in `spreadsheet_client.py`
- [x] Verify that `read_rows_from_google()` method returns data in the expected format
- [x] Add tests for spreadsheet reading if not already covered

### 4. Add the Task Handler Function in Research Daemon
- [x] Add a new method `do_import_companies_from_spreadsheet` in `ResearchDaemon` class:
  - [x] Connect to spreadsheet and fetch all company rows
  - [x] For each row, normalize company name for duplicate checking
  - [x] Check if company already exists in database
  - [x] Apply merge logic if duplicate exists
  - [x] Create new company if no duplicate exists
  - [x] Update task with progress information
  - [x] Generate summary statistics upon completion
- [x] Add handling of the new task type in `process_next_task`
- [x] Add tests for the new method using mock spreadsheet client

### 5. Implement Name Normalization and Duplicate Detection Logic
- [x] Review existing `normalize_company_name` function in `models.py`
- [x] Implement function to check for duplicate companies between spreadsheet and database
  - [x] First check using exact normalized name match
  - [ ] If no match, implement optional fuzzy matching with configurable threshold
  - [x] Return matched company or None
- [x] Add tests for duplicate detection logic:
  - [x] Test exact match cases
  - [ ] Test fuzzy match cases
  - [x] Test no-match cases

### 6. Implement Merge Logic for Company Data
- [ ] Create a new `merge_company_data` function that:
  - [ ] Takes a DB company and a spreadsheet company as input
  - [ ] Iterates through all fields in `CompaniesSheetRow`
  - [ ] For each field:
    - [ ] Check if spreadsheet has non-empty value
    - [ ] If so, use the spreadsheet value
    - [ ] If not, preserve the database value
  - [ ] Apply special handling for date fields (use most recent date)
  - [ ] Apply special handling for notes (append rather than replace)
  - [ ] Return the merged company object
- [ ] Add tests for merging functionality with various scenarios:
  - [ ] Test when spreadsheet data is more recent
  - [ ] Test when DB data has fields not in spreadsheet
  - [ ] Test when both have data in same fields
  - [ ] Test special handling for notes field (should append)
  - [ ] Test empty/null value handling

### 7. Update Database Schema (if needed)
- [ ] Check if database schema needs updates to track imported companies
- [ ] Create migration if necessary
- [ ] Add a new field to `CompanyStatus` to track import source and timestamp

### 8. Add API Endpoint for Initiating Import
- [ ] Add a new route in `server/app.py`:
  ```python
  config.add_route('import_companies', '/api/import_companies')
  ```
- [ ] Implement the endpoint to create a new import task
- [ ] Add tests for the new endpoint
- [ ] Add validation for request parameters

### 9. Add Progress Tracking for Import Task
- [ ] Update the task result schema to include:
  - [ ] Total companies found in spreadsheet
  - [ ] Number processed so far
  - [ ] Current company being processed
  - [ ] Number of companies created
  - [ ] Number of companies updated
  - [ ] Errors encountered
- [ ] Modify task handler to update progress as it processes companies
- [ ] Add tests for progress tracking:
  - [ ] Test progress updates at various stages
  - [ ] Test error handling during progress updates

### 10. Add Import Results Summary Logic
- [ ] Create a structure to report import results (total imported, duplicates, errors)
- [ ] Update the task handler to generate this summary
- [ ] Add tests for the summary generation
- [ ] Add error logging for failed imports

### 11. Implement Frontend Changes
- [ ] Add a new button to the UI for importing companies
- [ ] Add a modal dialog to confirm the import action with options
- [ ] Add progress indicator for ongoing import
- [ ] Add results display for completed import
- [ ] Add tests for new UI components

### 12. End-to-End Testing
- [ ] Create comprehensive integration tests for the entire import flow
- [ ] Test with actual spreadsheet data
- [ ] Verify correct handling of duplicates and merging

### 13. Documentation
- [ ] Update README with information about the new feature
- [ ] Add any necessary documentation for developers


### Merge Logic Considerations
- Need to identify which fields should be preserved from DB when merging
- Special handling for certain field types (dates, numbers, boolean values)
- Handling of notes fields (should they be appended rather than overwritten?)

### Frontend Considerations
- Include a confirmation dialog before starting import
- Show progress updates during import
- Display summary of results after import completes
- Handle error states gracefully

### Testing Strategy
- Unit tests for each component (normalization, merging, task handling)
- Integration tests for the full import flow
- UI tests for the new frontend components
