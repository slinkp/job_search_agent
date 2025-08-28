Plan: Implement company merging functionality (Issue #53)

We will implement a company merging system that allows combining duplicate companies when their aliases overlap. This includes backend merging logic, task management, API endpoints, and frontend UX for manual duplicate detection and merging.

0. Ground rules and definition of done

- [ ] Follow `feature-development-process.mdc`; keep edits ≤2–3 files/step, ≤100 LOC where possible; add tests; all tests must pass via `./test`.
- [ ] Acceptance criteria:
  - [ ] Users can manually mark companies as duplicates and merge them via UI
  - [ ] Backend can detect potential duplicates based on alias intersection
  - [ ] Merging preserves all data, with canonical company taking precedence
  - [ ] Duplicate company is soft-deleted after successful merge
  - [ ] All related data (messages, events, tasks) points to canonical company post-merge
  - [ ] Repository methods filter out soft-deleted companies by default
  - [ ] System can prompt users when potential duplicates are detected during research/ingestion

1. Data model: soft deletion support


- [ ] Migration file: `20250828125000_add_company_soft_delete.py`
    - [ ] Add `deleted_at` column to companies table
         - `deleted_at TEXT DEFAULT NULL` (ISO timestamp when company was soft-deleted)
    - [ ] Add index on `deleted_at` for efficient filtering
    - [ ] Tests: migration success, data consistency checks
- [ ] Repository changes:
  - [ ] Update `get_all()`, `get_by_normalized_name()` to select by `WHERE deleted_at IS NULL` by default
  - [ ] Update `get_all_messages()` to select where the associated company isn't deleted by default
  - [ ] Add optional `include_deleted: bool = False` parameter to bypass filter when needed
  - [ ] Add `soft_delete_company(company_id: str)` method to set `deleted_at = now()`
- [ ] Tests: verify soft-deleted companies are filtered out, can be included when requested
- [ ] Data validation script:
  - [ ] Check for orphaned aliases after any merges
  - [ ] Verify referential integrity of messages/events

2. Backend: duplicate detection logic

- [ ] New helper functions:
  - [ ] `find_potential_duplicates(company_id: str) -> List[str]`: find companies with overlapping aliases
  - [ ] `detect_alias_conflicts(alias: str) -> List[str]`: find existing companies with matching normalized alias
- [ ] Integration points:
  - [ ] Research completion: check for alias conflicts, log potential duplicates
  - [ ] Email ingestion: detect immediate duplicates when creating companies
  - [ ] Manual alias creation: warn if alias matches existing companies
- [ ] Tests: various alias overlap scenarios, edge cases with inactive aliases

3. Backend: company merging logic

- [ ] Core merge function: `merge_companies(canonical_id: str, duplicate_id: str) -> bool`:
  - [ ] Validate both companies exist and are not deleted
  - [ ] Use canonical company's name as final name
  - [ ] Migrate all aliases from duplicate to canonical (preserve source, update company_id)
  - [ ] Merge `CompaniesSheetRow` fields: canonical takes precedence, fill empty fields from duplicate
  - [ ] Migrate all `recruiter_messages` to point to canonical company
  - [ ] Migrate all `events` to point to canonical company  
  - [ ] Soft-delete the duplicate company
- [ ] Validation: prevent merging company with itself, handle already-deleted companies
- [ ] Tests: comprehensive merge scenarios, data preservation, error cases

4. Task system: merge_companies task type

- [ ] Add `MERGE_COMPANIES = "merge_companies"` to `TaskType` enum
- [ ] Task args: `{"canonical_company_id": str, "duplicate_company_id": str}`
- [ ] Research daemon integration: handle `merge_companies` tasks
- [ ] Error handling: rollback on failure, detailed error messages
- [ ] Tests: successful merge task, error scenarios, task status updates

5. API: company merging endpoints

- [ ] `POST /api/companies/:id/merge` - start merge task:
  - [ ] Request body: `{"duplicate_company_id": str}`
  - [ ] Validation: both companies exist, not same company, not already deleted
  - [ ] Creates and returns task_id for merge operation
- [ ] `GET /api/companies/:id/potential-duplicates` - find potential duplicates:
  - [ ] Returns list of companies with overlapping aliases
  - [ ] Include alias overlap details for user decision
- [ ] Tests: API validation, response shapes, error cases

6. Frontend: manual duplicate detection UI

- [ ] Company detail page: add "Mark as Duplicate" button
  - [ ] Opens search modal for finding potential merge target
  - [ ] Search by company name with autocomplete
  - [ ] Show alias overlap information to help user decide
  - [ ] Confirm merge with clear indication of which company survives
- [ ] Search functionality:
  - [ ] Type-ahead search across company names and aliases
  - [ ] Exclude current company and already-deleted companies from results
  - [ ] Highlight matching aliases between companies
- [ ] Tests: UI interactions, search functionality, merge confirmation flow

7. Frontend: duplicate detection prompts

- [ ] Research completion notifications:
  - [ ] Show banner/modal when research finds potential duplicates
  - [ ] Allow user to review and merge or dismiss
- [ ] Email scanning notifications:
  - [ ] Prompt user when duplicate company detected during ingestion
  - [ ] Option to merge immediately or create separate company
- [ ] Tests: notification display, user interaction flows

8. Test inventory

- [ ] Models/repo: soft delete filtering, merge logic, data migration
- [ ] Task system: merge task creation, execution, error handling  
- [ ] API: merge endpoints, validation, response formats
- [ ] Frontend: duplicate detection UI, search, merge confirmation
- [ ] Integration: research/ingestion duplicate detection prompts
- [ ] Data integrity: migration, consistency checks

Notes

- This builds on the existing alias system from Issue #10 to detect duplicates via alias overlap
- Soft deletion preserves audit trail while hiding duplicates from normal operations
- Task-based merging allows for proper error handling and rollback capabilities
- Frontend provides both manual and prompted duplicate detection workflows
