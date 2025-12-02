// Company-related pure utilities

/**
 * Format research errors in a user-friendly string.
 * Accepts a company object and inspects `company.research_errors`.
 */
export function formatResearchErrors(company) {
  if (!company || !company.research_errors) return "";

  const errors = company.research_errors;

  // If it's already a formatted string, just return it
  if (typeof errors === "string") {
    return errors;
  }

  // If it's an array of objects or strings, format it
  if (Array.isArray(errors)) {
    return errors
      .map((err) => {
        if (typeof err === "string") return err;
        if (err && err.step && err.error) return `${err.step}: ${err.error}`;
        try {
          return JSON.stringify(err);
        } catch {
          return String(err);
        }
      })
      .join("; ");
  }

  // Fallback for unknown formats
  try {
    return JSON.stringify(errors);
  } catch {
    return String(errors);
  }
}

/**
 * Filter companies by app-level filterMode for company management view.
 * Modes: 'reply-sent', 'reply-not-sent', 'researched', 'not-researched', or default 'all'
 */
export function filterCompanies(companies, filterMode) {
  const list = Array.isArray(companies) ? companies : [];
  switch (filterMode) {
    case "reply-sent":
      return list.filter((c) => Boolean(c.sent_at));
    case "reply-not-sent":
      return list.filter((c) => !c.sent_at);
    case "researched":
      return list.filter((c) => Boolean(c.research_completed_at));
    case "not-researched":
      return list.filter((c) => !c.research_completed_at);
    default:
      return list.slice();
  }
}

/**
 * Sort companies by a field with optional ascending/descending.
 * Special handling for updated_at treated as a date.
 */
export function sortCompanies(companies, sortField, sortAsc = true) {
  const list = Array.isArray(companies) ? companies.slice() : [];
  if (!sortField) return list;
  return list.sort((a, b) => {
    const isDateField = sortField === "updated_at" || sortField === "activity_at";
    const aVal = isDateField
      ? new Date(a?.[sortField] || 0).getTime()
      : a?.[sortField];
    const bVal = isDateField
      ? new Date(b?.[sortField] || 0).getTime()
      : b?.[sortField];
    const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
    return sortAsc ? cmp : -cmp;
  });
}

/**
 * Ensure a company object has normalized structure (e.g., details is an object).
 */
export function normalizeCompany(company) {
  if (!company || typeof company !== "object") return { details: {} };
  return {
    ...company,
    details: company.details || {},
  };
}

/**
 * Normalize an array of companies.
 */
export function normalizeCompanies(companies) {
  const list = Array.isArray(companies) ? companies : [];
  return list.map((c) => normalizeCompany(c));
}

/**
 * Compute overlapping aliases (case-insensitive) between two companies.
 */
export function aliasOverlap(companyA, companyB) {
  if (!companyA?.aliases || !companyB?.aliases) return [];
  const a = companyA.aliases.map((x) => String(x.alias || "").toLowerCase());
  const b = companyB.aliases.map((x) => String(x.alias || "").toLowerCase());
  const setA = new Set(a);
  const overlaps = [];
  for (const alias of b) {
    if (setA.has(alias)) overlaps.push(alias);
  }
  return overlaps;
}

/**
 * Find duplicate candidate companies by name or alias substring match.
 * Excludes the current company and any soft-deleted companies.
 */
export function findDuplicateCandidates(companies, currentCompany, query) {
  const list = Array.isArray(companies) ? companies : [];
  const q = String(query || "")
    .toLowerCase()
    .trim();
  if (!q) return [];
  const currentId = currentCompany?.company_id;
  // Build scored candidates so exact/prefix matches rank above generic substrings
  const candidates = [];
  for (const company of list) {
    if (!company) continue;
    if (currentId && company.company_id === currentId) continue;
    if (company.deleted_at) continue;

    const name = String(company.name || "").toLowerCase();
    const aliases = Array.isArray(company.aliases) ? company.aliases : [];
    const aliasStrings = aliases.map((a) =>
      String(a.alias || "").toLowerCase()
    );

    let score = 0;
    // Name scoring
    if (name === q) score = Math.max(score, 100);
    else if (name.startsWith(q)) score = Math.max(score, 70);
    else if (name.includes(q)) score = Math.max(score, 40);

    // Alias scoring (slightly lower than exact name equality but above name prefix/substring when exact)
    for (const alias of aliasStrings) {
      if (alias === q) score = Math.max(score, 90);
      else if (alias.startsWith(q)) score = Math.max(score, 60);
      else if (alias.includes(q)) score = Math.max(score, 35);
    }

    if (score > 0) {
      candidates.push({ company, score });
    }
  }

  // Sort by score desc, then shorter name first, then lexicographically
  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const an = String(a.company.name || "");
    const bn = String(b.company.name || "");
    if (an.length !== bn.length) return an.length - bn.length;
    return an.localeCompare(bn);
  });

  return candidates.map((c) => c.company);
}

/**
 * Normalize a company name for equality comparison on the frontend.
 *
 * This intentionally mirrors the spirit (but not the exact details) of the
 * backend `normalize_company_name` helper:
 * - trims whitespace
 * - lowercases
 * - normalizes "&" to "and"
 * - collapses internal whitespace
 */
export function normalizeCompanyNameForComparison(name) {
  if (!name) return "";
  let result = String(name).trim().toLowerCase();
  result = result.replace(/&/g, "and");
  // Collapse any internal whitespace to a single space
  result = result.replace(/\s+/g, " ");
  return result;
}
