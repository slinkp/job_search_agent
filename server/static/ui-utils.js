// Shared UI Utilities Module
// Provides common UI functions that can be used by multiple components

/**
 * Format a date string for display in the companies view
 * Shows date in YYYY/MM/DD format with time and "days ago"
 */
export function formatRecruiterMessageDate(dateString) {
  if (!dateString) return "";

  const date = new Date(dateString);
  const now = new Date();

  // Calculate days ago
  const diffTime = Math.abs(now - date);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  // Format the date as YYYY/MM/DD
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  // Format the time as h:mm am/pm
  let hours = date.getHours();
  const ampm = hours >= 12 ? "pm" : "am";
  hours = hours % 12;
  hours = hours ? hours : 12; // the hour '0' should be '12'
  const minutes = String(date.getMinutes()).padStart(2, "0");

  return `${year}/${month}/${day} ${hours}:${minutes}${ampm} (${diffDays} days ago)`;
}

/**
 * Format a date string for display in the daily dashboard
 * Shows date in locale format with time
 */
export function formatMessageDate(dateString) {
  if (!dateString) return "Unknown date";
  try {
    const date = new Date(dateString);
    return (
      date.toLocaleDateString() +
      " " +
      date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    );
  } catch (error) {
    return "Invalid date";
  }
}

/**
 * Show an error message to the user
 * Currently uses alert, but can be enhanced with toast notifications later
 */
export function showError(message) {
  alert(message); // We can make this fancier later with a toast or custom modal
}

/**
 * Show a success message to the user
 * Currently uses alert, but can be enhanced with toast notifications later
 */
export function showSuccess(message) {
  alert(message); // Simple success notification, can be improved later
}

/**
 * Check if a value is a valid URL
 */
export function isUrl(value) {
  return typeof value === "string" && value.startsWith("http");
}
