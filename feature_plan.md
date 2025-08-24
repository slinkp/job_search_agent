Plan: Fix company name normalization issues (Issue #10)

We will add a first-class, many-to-one alias model to support arbitrary company name variations, improve Notion-hosted name extraction. We will migrate the DB to persist aliases and expose minimal APIs/UI to manage them.

0. Ground rules and definition of done

- [ ] Follow `feature-development-process.mdc`; keep edits ≤2–3 files/step, ≤100 LOC where possible; add tests; all tests must pass via `./test`.
- [ ] Acceptance criteria:
  - [ ] Notion-hosted pages never set company name to "notion"; true name is preserved or left blank if unknown.
  - [ ] Arbitrary aliases can be stored per company; aliases are used for matching
  - [ ] The current notion of "canonical" name is whatever's in `company.name`
  - [ ] Manual alias CRUD supported (create/update/deactivate); changes persist and affect all relevant flows.
  - [ ] Matching remains stable; no regressions to existing normalization behavior.

1. Data model: first-class aliases

- [x] Migration: create table `company_aliases`:
  - id (PK), company_id (FK -> companies.company_id)
  - alias TEXT NOT NULL
  - normalized_alias TEXT NOT NULL (via current `normalize_company_name`)
  - source TEXT NOT NULL DEFAULT "auto" (enum-like: "manual" | "auto" | "seed" | "levels")
  - is_active INTEGER NOT NULL DEFAULT 1
  - created_at, updated_at
- [x] Indexes/constraints:
  - [x] UNIQUE(company_id, normalized_alias) WHERE is_active=1
  - [x] INDEX on normalized_alias for fast lookups
- [x] Backfill:
  - [x] Add each company's current `name` as an alias (`source="seed"`).
  - [x] Seed known mappings (e.g., "amazon web services", "aws" → company for "Amazon")

2. Normalization and matching semantics

- [x] New helpers:
  - [x] `resolve_alias(name: str) -> company_id | None`:
        lookup by `normalized_alias` in `company_aliases`.
- [x] Repository changes:
  - [x] Update `CompanyRepository.get_by_normalized_name` to use `resolve_alias` and return the matching company.
- [x] Tests: multi-alias per company, inactive alias ignored, uniqueness errors.

3. API: alias management and payload shape

- [x] `GET /api/companies/:id` and list endpoints include:
  - [x] `aliases`: [{ alias, source, is_active }]
- [x] `POST /api/companies/:id/aliases` (create), `PUT /api/companies/:id/aliases/:alias_id` (update), `DELETE` or `PATCH is_active=false` (deactivate).
  - [x] POST will create an alias with source `manual`.
  - [x] Payload should also allow a flag to set the alias as canonical, in which case `company.name` and `company.details.name` are also updated.  But their old value(s) should be preserved in the alias table, if not already there.
- [x] Payload validation: normalize server-side; prevent duplicates.
- [x] Tests: API CRUD alias lifecycle, response shapes, validation.

4. Researcher and ingestion: Notion-hosted guardrails

- [x] In `TavilyRAGResearchAgent.update_company_info_from_dict`:
  - [x] Ignore generic host names ("notion", "linkedin", variations) similarly to placeholders.
  - [x] Prefer existing canonical `company.name` **unless it's a placeholder**, in which case, replace it.
  - [x] Whenever an alternate name is discovered in research, record it as `source="auto"` alias (active)
- [x] Tests in `tests/test_company_researcher.py`: Notion scenarios; verify no "notion" names.

5. Research integration

- [x] In `levels_searcher`: try canonical first; if that doesn't work, then iterate through the others, starting with the `manual` sourced ones first.  Stop on the first name that works and **set it as canonical**. Log an error if none work.
- [x] In `linkedin_searcher`: try canonical first; if that doesn't work, then iterate through the others, starting with the `manual` sourced ones first.  Stop on the first name that works and **set it as canonical**. Log an error if none work.

6. Migration and backfill scripts

- [x] Add migration file `20250822051100_add_company_aliases.py` creating table, indexes.
- [x] Seed script/migration step:
  - [x] Insert canonical name aliases for all companies (global).
- [x] Logging: counts of inserted/updated/duplicates.

7. Minimal frontend surface (optional but recommended)

- [ ] Companies page: show aliases list and allow add/deactivate.
    - [x] Show aliases list (display only)
    - [ ] "Add" form needs a checkbox option to set this new alias as canonical. **Enabled by default**
- [ ] Keep UI simple; reuse existing fetch helpers.
- [x] Tests: unit for rendering and basic interactions.

8. Test inventory

- [ ] Models/repo: alias CRUD, matching precedence (canonical, manual, auto, seed), inactive handling, uniqueness.
- [ ] Researcher: Notion guardrails.
- [ ] Levels: alias usage.
- [ ] Linkedin: alias usage.
- [ ] API: payload shape and validation.
- [ ] Backfill: idempotency and counts.

9. Docs and cleanup

- [ ] Update README "Company name normalization issues" with new capabilities.
- [ ] Add examples for common cases (AWS/Amazon, Meta/Facebook, Alphabet/Google).

Notes

- This plan embraces DB migration to create a proper alias model that can handle arbitrary name variations.
- The migration includes seeding existing names as aliases to maintain backward compatibility.
