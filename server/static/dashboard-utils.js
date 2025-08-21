// Dashboard utility helpers extracted from daily-dashboard.js

/**
 * Filter messages by filterMode
 * @param {Array<any>} messages
 * @param {string} filterMode - one of 'all' | 'archived' | 'replied' | 'not-replied'
 * @returns {Array<any>}
 */
export function filterMessages(messages, filterMode) {
  const input = Array.isArray(messages) ? messages : [];
  switch (filterMode) {
    case "archived":
      return input.filter(
        (message) => message.archived_at || message.company_archived_at
      );
    case "replied":
      return input.filter((message) => message.reply_sent_at);
    case "not-replied":
      return input.filter((message) => !message.reply_sent_at);
    case "all":
    default:
      return input;
  }
}

/**
 * Sort messages by date ascending/descending
 * Handles null/undefined dates by pushing them to the end
 * @param {Array<any>} messages
 * @param {boolean} sortNewestFirst
 * @returns {Array<any>}
 */
export function sortMessages(messages, sortNewestFirst) {
  if (!Array.isArray(messages) || messages.length === 0) return [];
  const copy = [...messages];
  return copy.sort((a, b) => {
    const dateA = a?.date ? new Date(a.date).getTime() : null;
    const dateB = b?.date ? new Date(b.date).getTime() : null;

    if (dateA === null && dateB === null) return 0;
    if (dateA === null) return 1;
    if (dateB === null) return -1;

    return sortNewestFirst ? dateB - dateA : dateA - dateB;
  });
}

/**
 * Parse filter/sort state from a search string
 * @param {string} search
 * @returns {{ filterMode: string, sortNewestFirst: boolean }}
 */
export function parseUrlState(search) {
  const params = new URLSearchParams(search || "");
  const filterParam = params.get("filterMode");
  const sortParam = params.get("sort");

  const validFilters = new Set(["all", "archived", "replied", "not-replied"]);
  const filterMode = validFilters.has(filterParam || "")
    ? filterParam
    : "all";

  const sortNewestFirst = sortParam
    ? sortParam === "newest"
    : true; // default newest

  return { filterMode, sortNewestFirst };
}

/**
 * Build updated search string with given state while preserving existing params
 * @param {string} currentSearch
 * @param {{ filterMode?: string, sortNewestFirst?: boolean }} state
 * @returns {string} search string without leading '?'
 */
export function buildUpdatedSearch(currentSearch, state) {
  const params = new URLSearchParams(currentSearch || "");
  if (state.filterMode) params.set("filterMode", state.filterMode);
  if (typeof state.sortNewestFirst === "boolean")
    params.set("sort", state.sortNewestFirst ? "newest" : "oldest");
  return params.toString();
}

/**
 * Get heading text for the current filter
 * @param {string} filterMode
 * @param {number} count
 * @returns {string}
 */
export function getFilterHeading(filterMode, count) {
  const safeCount = Number.isFinite(count) ? count : 0;
  switch (filterMode) {
    case "all":
      return `All Messages (${safeCount})`;
    case "not-replied":
      return `Unreplied Messages (${safeCount})`;
    case "archived":
      return `Archived Messages (${safeCount})`;
    case "replied":
      return `Replied Messages (${safeCount})`;
    default:
      return `Messages (${safeCount})`;
  }
}


