// URL-related helpers used by the frontend

/**
 * Set the include_all parameter on a URL object
 */
export function setIncludeAllParam(url, includeAll) {
  if (includeAll) {
    url.searchParams.set("include_all", "true");
  } else {
    url.searchParams.delete("include_all");
  }
}

/**
 * Build a hash for a company (used for scrolling)
 */
export function buildHashForCompany(companyId) {
  return `#${encodeURIComponent(companyId)}`;
}

/**
 * Parse view mode from URL search parameters
 */
export function parseViewFromUrl(search) {
  const params = new URLSearchParams(search || "");
  return params.get("view") === "daily" ? "daily_dashboard" : "company_management";
}

/**
 * Common URL manipulation utilities
 */
export const urlUtils = {
  /**
   * Create a new URL object from current location
   */
  createUrl() {
    return new URL(window.location);
  },

  /**
   * Update URL parameters and replace state
   */
  updateUrlParams(params, replaceState = true) {
    const url = this.createUrl();
    Object.entries(params).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        url.searchParams.delete(key);
      } else {
        url.searchParams.set(key, value);
      }
    });
    
    if (replaceState) {
      window.history.replaceState({}, "", url);
    } else {
      window.history.pushState({}, "", url);
    }
    return url;
  },

  /**
   * Remove URL parameters
   */
  removeUrlParams(keys) {
    const url = this.createUrl();
    keys.forEach(key => url.searchParams.delete(key));
    window.history.replaceState({}, "", url);
    return url;
  },

  /**
   * Set URL hash
   */
  setHash(hash) {
    const url = this.createUrl();
    url.hash = hash;
    window.history.replaceState({}, "", url);
    return url;
  }
};

// Dashboard URL sync helpers (extracted from daily-dashboard.js)
import { buildUpdatedSearch, parseUrlState } from "./dashboard-utils.js";

export function readDailyDashboardStateFromUrl(search) {
  return parseUrlState(search || window.location.search || "");
}

export function updateDailyDashboardUrlWithState(filterMode, sortNewestFirst) {
  const currentSearch = window.location.search || "";
  const search = buildUpdatedSearch(currentSearch, { filterMode, sortNewestFirst });
  const newUrl = `${window.location.pathname || "/"}?${search}${window.location.hash || ""}`.replace(
    /([^:])\/\//g,
    "$1/"
  );
  window.history.replaceState({ ...window.history.state, filtersUpdated: true }, "", newUrl);
  return newUrl;
}
