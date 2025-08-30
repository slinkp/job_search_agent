Plan: Implement company merging functionality (Issue #53)

We will implement a company merging system that allows combining duplicate companies when their aliases overlap. This includes backend merging logic, task management, API endpoints, and frontend UX for manual duplicate detection and merging.

0. Ground rules and definition of done

- [ ] Follow `yolo.mdc`; keep edits ≤2–3 files/step, ≤100 LOC where possible; add tests; all tests must pass via `./test`.
- [ ] Acceptance criteria:
  - [ ] Users can manually mark companies as duplicates and merge them via UI
  - [ ] Backend can detect potential duplicates based on alias intersection
  - [ ] Merging preserves all data, with canonical company taking precedence
  - [ ] Duplicate company is soft-deleted after successful merge
  - [ ] All related data (messages, events, tasks) points to canonical company post-merge
  - [ ] Repository methods filter out soft-deleted companies by default
  - [ ] System can prompt users when potential duplicates are detected during research/ingestion

1. Data model: soft deletion support

- [x] Migration file: `20250828125000_add_company_soft_delete.py` with tests
    - [x] Add `deleted_at` column to companies table
         - `deleted_at TEXT DEFAULT NULL` (ISO timestamp when company was soft-deleted)
    - [x] Add index on `deleted_at` for efficient filtering
    - [x] Migration success, data consistency checks
- [x] Repository changes with tests:
  - [x] Update `get_all()`, `get_by_normalized_name()` to select by `WHERE deleted_at IS NULL` by default
  - [x] Update `get_all_messages()` to select where the associated company isn't deleted by default
  - [x] Add optional `include_deleted: bool = False` parameter to bypass filter when needed
  - [x] Add `soft_delete_company(company_id: str)` method to set `deleted_at = now()`
  - [x] Verify soft-deleted companies are filtered out, can be included when requested
- [x] Data validation script:
  - [x] Check for orphaned aliases after any merges

2. Backend: duplicate detection logic

- [x] New helper functions:
  - [x] `detect_alias_conflicts(alias: str) -> List[str]`: find existing companies with matching normalized alias. Test edge cases with inactive aliases, soft-deleted companies.
  - [x] `find_potential_duplicates(company_id: str) -> List[str]`: find companies with overlapping aliases.  Test various alias overlap scenarios. 
- [x] Integration points with existing code:
  - [x] Research completion: check for alias overlap, add to task result. For now just log potential duplicates
  - [x] Email ingestion: detect immediate duplicates when creating aliases for new companies. For now just log these
  - [x] Manual alias creation API: warn if alias matches existing companies

3. Backend: company merging logic

- [x] Core merge function: `merge_companies(canonical_id: str, duplicate_id: str) -> bool`:
  - [x] Validate both companies exist and are not deleted. Test error cases.
  - [x] Use canonical company's name as final name
  - [x] Migrate all aliases from duplicate to canonical (preserve source, update company_id). Test data preservation.
  - [x] Merge `CompaniesSheetRow` fields: canonical takes precedence, fill empty fields from duplicate. Test merge scenarios.
  - [x] Migrate all `recruiter_messages` to point to canonical company
  - [x] Migrate all `events` to point to canonical company  
  - [x] Soft-delete the duplicate company
- [x] Validation: prevent merging company with itself, handle already-deleted companies

4. Task system: merge_companies task type

- [x] Add `MERGE_COMPANIES = "merge_companies"` to `TaskType` enum
- [x] Create task with args: `{"canonical_company_id": str, "duplicate_company_id": str}`
- [x] Research daemon integration: handle `merge_companies` tasks. Test successful merge task.
- [x] Error handling: rollback on failure, detailed error messages. Test error scenarios and rollback.

5. API: company merging endpoints

- [x] `POST /api/companies/:id/merge` - start merge task:
  - [x] Request body: `{"duplicate_company_id": str}`
  - [x] Validation: both companies exist, not same company, not already deleted. Test validation error cases.
  - [x] Creates and returns task_id for merge operation. Test response shape.
- [x] `GET /api/companies/:id/potential-duplicates` - find potential duplicates:
  - [x] Returns list of companies with overlapping aliases. Test response format.
  - [x] Include alias overlap details for user decision

6. Frontend: manual duplicate detection UI

- [x] Company detail page: add "Mark as Duplicate" button
  - [x] Opens search modal for finding potential merge target. Test modal opens.
  - [x] Search by company name with autocomplete
  - [x] Show alias overlap information to help user decide
  - [x] Confirm merge with clear indication of which company survives. Test confirmation flow.
- [x] Search functionality:
  - [x] Type-ahead search across company names and aliases. Test search functionality.
  - [x] Exclude current company and already-deleted companies from results
  - [x] Highlight matching aliases between companies

7. Frontend: duplicate detection prompts

- [x] Research completion notifications:
  - [x] Show banner/modal when research finds potential duplicates. Test notification display.
  - [x] Allow user to review and merge or dismiss. Test user interaction flows.
- [ ] Email scanning notifications:
  - [ ] Prompt user when duplicate company detected during ingestion
  - [ ] Option to merge immediately or create separate company

8. Integration verification

- [ ] End-to-end testing: complete merge workflow from detection through completion
- [ ] Data integrity: verify no orphaned data after merges, referential integrity maintained

Notes

- This builds on the existing alias system from Issue #10 to detect duplicates via alias overlap
- Soft deletion preserves audit trail while hiding duplicates from normal operations
- Task-based merging allows for proper error handling and rollback capabilities
- Frontend provides both manual and prompted duplicate detection workflows
