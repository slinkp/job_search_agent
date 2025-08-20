// URL-related helpers used by the frontend

/**
 * Determine app view mode from URL search params.
 * Returns one of: 'daily_dashboard' or 'company_management'.
 */
export function parseViewFromUrl(search) {
  try {
    const params = new URLSearchParams(search || "");
    const viewParam = params.get("view");
    return viewParam === "daily" ? "daily_dashboard" : "company_management";
  } catch {
    return "company_management";
  }
}

/**
 * Set or remove include_all search param on a URL object.
 * Mutates and returns the same URL instance for chaining.
 */
export function setIncludeAllParam(url, includeAll) {
  if (!(url instanceof URL)) {
    throw new Error("setIncludeAllParam expects a URL instance");
  }
  if (includeAll) {
    url.searchParams.set("include_all", "true");
  } else {
    url.searchParams.delete("include_all");
  }
  return url;
}

/**
 * Build the URL hash for a company anchor (encoded id string, no leading '#').
 */
export function buildHashForCompany(companyId) {
  return encodeURIComponent(companyId ?? "");
}
