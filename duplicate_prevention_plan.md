# Plan: Prevent Duplicate Company Entries

This plan outlines the steps to prevent duplicate companies (based on name) from being added to the database. Each step should result in a working state with passing tests.

- [ ] **Step 1: Normalize Company Names on Save:**
    - Locate the `CompanyRepository` method responsible for saving/adding new companies.
    - Modify this method to normalize the company name (e.g., convert to lowercase, strip leading/trailing whitespace) *before* it is persisted to the database.
    - Update any existing tests for this save method to reflect the normalization. Add new tests if necessary to specifically verify the normalization logic.

- [ ] **Step 2: Add Repository Method for Existence Check:**
    - Add a new method to the `CompanyRepository` (e.g., `company_exists_by_name(name: str) -> bool`).
    - This method should take a company name, normalize it using the same logic as in Step 1, and query the database to see if a company with that normalized name exists.
    - Add unit tests for this new repository method.

- [ ] **Step 3: Implement Check Before Adding:**
    - Identify the code location(s) where new companies are typically created and added (e.g., after processing an email, in the manual add API endpoint).
    - Before calling the repository's save/add method, call the new `company_exists_by_name` method using the potential new company's name.
    - If the method returns `True`, skip the step of saving the new company.
    - Consider logging a message (e.g., DEBUG or INFO level) indicating that a duplicate was detected and not added.

- [ ] **Step 4: Add Integration Tests:**
    - Write integration tests that specifically target the duplicate prevention logic.
    - These tests should:
        - Verify that a truly new company *is* added successfully.
        - Verify that attempting to add a company with the same name (ignoring case and whitespace differences) as an existing one *does not* result in a new database entry.
        - Check that the total number of companies in the database does not increase when a duplicate is processed. 