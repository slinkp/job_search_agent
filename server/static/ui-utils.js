// Shared UI Utilities Module
// Provides common UI functions that can be used by multiple components

/**
 * Format a date string for display
 * @param {string} dateString - The date string to format
 * @param {string} format - The format to use: 'detailed' (with days ago) or 'simple' (locale format)
 * @returns {string} The formatted date string
 */
export function formatDate(dateString, format = 'simple') {
  if (!dateString) return format === 'simple' ? "Unknown date" : "";

  try {
    const date = new Date(dateString);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return format === 'simple' ? "Invalid date" : "";
    }
    
    if (format === 'detailed') {
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
    } else {
      // Simple format: locale date + time
      return (
        date.toLocaleDateString() +
        " " +
        date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      );
    }
  } catch (error) {
    return format === 'simple' ? "Invalid date" : "";
  }
}

/**
 * Format a date string for display in the companies view
 * Shows date in YYYY/MM/DD format with time and "days ago"
 * @deprecated Use formatDate(dateString, 'detailed') instead
 */
export function formatRecruiterMessageDate(dateString) {
  return formatDate(dateString, 'detailed');
}

/**
 * Format a date string for display in the daily dashboard
 * Shows date in locale format with time
 * @deprecated Use formatDate(dateString, 'simple') instead
 */
export function formatMessageDate(dateString) {
  return formatDate(dateString, 'simple');
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

/**
 * Common confirmation dialogs used throughout the application
 */
export const confirmDialogs = {
  /**
   * Confirm archiving a message without replying
   */
  archiveWithoutReply() {
    return confirm("Are you sure you want to archive this message without replying?");
  },

  /**
   * Confirm sending and archiving a message
   */
  sendAndArchive() {
    return confirm("Are you sure you want to send this reply and archive the message?");
  }
};

/**
 * Common error logging utilities for consistent error handling
 */
export const errorLogger = {
  /**
   * Log a "Failed to" error with consistent formatting
   */
  logFailedTo(action, error) {
    console.error(`Failed to ${action}:`, error);
  },

  /**
   * Log a generic error with consistent formatting
   */
  logError(message, error) {
    console.error(message, error);
  }
};

/**
 * Common modal utilities for consistent modal handling
 */
export const modalUtils = {
  /**
   * Show a modal by ID
   */
  showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.showModal();
    } else {
      console.error(`Modal with ID '${modalId}' not found`);
    }
  },

  /**
   * Close a modal by ID
   */
  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.close();
    } else {
      console.error(`Modal with ID '${modalId}' not found`);
    }
  },

  /**
   * Common modal IDs used throughout the application
   */
  modalIds: {
    EDIT: 'editModal',
    RESEARCH_COMPANY: 'research-company-modal',
    IMPORT_COMPANIES: 'import-companies-modal'
  }
};
