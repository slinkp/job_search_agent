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
  const q = String(query || "").toLowerCase().trim();
  if (!q) return [];
  const currentId = currentCompany?.company_id;
  return list.filter((company) => {
    if (!company) return false;
    if (currentId && company.company_id === currentId) return false;
    if (company.deleted_at) return false;
    const name = String(company.name || "").toLowerCase();
    if (name.includes(q)) return true;
    const aliases = Array.isArray(company.aliases) ? company.aliases : [];
    return aliases.some((a) => String(a.alias || "").toLowerCase().includes(q));
  });
}
