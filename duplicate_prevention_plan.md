# Plan: Prevent Duplicate Company Entries

This plan outlines the steps to prevent duplicate companies (based on name) from being added to the database. Each step should result in a working state with passing tests.

- [x] **Define Normalization:** strip, lowercase, and collapse internal
      whitespace to single dashes (based on existing `_generate_company_id` logic).
- [x] **Implement Normalization Utility:** Create a simple, reusable function `normalize_company_name(name: str) -> str` (perhaps in `models.py`) that performs `name.strip().lower()`.
- [x] **Test Normalization Utility:** Add unit tests for the new
      `normalize_company_name` function.
- [ ] Find any code where we already normalize company names to company ID and
      call this new function. Confirm that all existing tests pass.
- [ ] **Add `CompanyRepository.get_by_normalized_name`:**
    - [ ] Add a new method `get_by_normalized_name(self, name: str) -> Optional[Company]` to `models.CompanyRepository`.
    - [ ] This method should take a company name, normalize it using
          `normalize_company_name`, and query the database for a company where
          its `name` matches when normalized the same way (TBD how best to do
          this as we don't want to duplicate the normalization logic in sqlite
          and we may do further normalization in future;
          suggest some alternatives when we get to this step)
    - [ ] If a match is found, deserialize and return the `Company` object; otherwise, return `None`.
    - [ ] **Test `CompanyRepository.get_by_normalized_name`:** Add unit tests for the new repository method, testing both finding and not finding companies, including case/whitespace variations.
- [ ] **Modify Company Creation Logic:**
    - [ ] Locate the points in `research_daemon.py` and any other files where a
          new `Company` object is instantiated *before* being passed to
          `CompanyRepository.create` or `CompanyRepository
    - [ ] Before calling `repo.create(company)`, call `existing_company = repo.get_by_normalized_name(company_name)`.
    - [ ] If `existing_company` is not `None`, do *not* call `repo.create`. Instead, use the `existing_company` for subsequent operations (like associating the message or task).
    - [ ] Log a message at INFO when a duplicate is detected and creation is skipped.
- [ ] **Update/Add Integration Tests:**
    - Review existing integration tests where companies are created to ensure they account for the new duplicate check.
    - Add new integration tests specifically verifying that processing input for a company name that already exists (normalized) does not create a new database entry, but potentially associates the new data (like a message) with the existing company. 
