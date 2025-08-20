/**
 * Alpine.js Test Helper
 * This file provides utilities for testing Alpine.js components in a Node.js environment
 */

import { vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

let Alpine;

/**
 * Setup Alpine.js for testing
 * @returns {Object} Alpine instance
 */
export async function setupAlpine() {
  // Create a document before importing Alpine
  setupDocumentWithIndexHtml(document);

  // Create a proper MutationObserver mock
  if (
    !global.MutationObserver ||
    global.MutationObserver.toString().includes("class MutationObserver")
  ) {
    global.MutationObserver = createMockMutationObserver();
  }

  // Mock additional DOM methods that Alpine might use
  setupDomMocks();

  // Use fake timers to prevent Alpine's plugin warning system from running
  vi.useFakeTimers();

  // Import and initialize Alpine
  if (!Alpine) {
    Alpine = (await import("alpinejs")).default;
    window.Alpine = Alpine;

    // Register minimal component stubs required by index.html so Alpine init doesn't error
    Alpine.data("companyList", () => createMinimalCompanyList());
    Alpine.data("dailyDashboard", () => createMinimalDailyDashboard());
  }

  // Disable Alpine's warning system to prevent unhandled errors
  Alpine.onWarning = () => {};

  // Start Alpine (initialize), but swallow init failures since tests don't need full app boot
  try {
    Alpine.start();
  } catch (err) {
    // Intentionally ignore init errors caused by app templates referencing real app data
  }

  return Alpine;
}

/**
 * Create a mock MutationObserver that works with Alpine.js
 */
function createMockMutationObserver() {
  return class MutationObserver {
    constructor(callback) {
      this.callback = callback;
      this.records = [];
      this.observing = false;
    }

    observe() {
      this.observing = true;
    }

    disconnect() {
      this.observing = false;
    }

    takeRecords() {
      const records = [...this.records];
      this.records = [];
      return records;
    }

    // Simulate a mutation for testing
    trigger(mutations) {
      if (this.observing) {
        this.callback(mutations || [], this);
      }
    }
  };
}

/**
 * Setup additional DOM mocks for testing
 */
function setupDomMocks() {
  // Mock showModal and close methods on dialog element
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function () {};
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function () {};
  }
}

// Minimal stubs to satisfy x-data/x-init and x-bind expressions in index.html
function createMinimalCompanyList() {
  return {
    loading: false,
    filterMode: "all",
    sortField: "name",
    sortAsc: true,
    companies: [],
    showArchived: false,
    editingCompany: null,
    editingReply: "",
    researchCompanyForm: { url: "", name: "" },
    importingCompanies: false,
    importStatus: null,
    researchingCompany: false,
    init() {},
    toggleViewMode() {},
    isCompanyManagementView() {
      return true;
    },
    isDailyDashboardView() {
      return false;
    },
    toggleShowArchived() {
      this.showArchived = !this.showArchived;
    },
    toggleSort(field) {
      this.sortField = field;
    },
    formatRecruiterMessageDate() {
      return "";
    },
    formatResearchErrors() {
      return "";
    },
    navigateToCompany() {},
    navigateToMessage() {},
    showResearchCompanyModal() {},
    closeResearchCompanyModal() {},
    submitResearchCompany() {},
    showImportCompaniesModal() {},
    closeImportCompaniesModal() {},
    confirmImportCompanies() {},
    importCompaniesFromSpreadsheet() {},
    editReply() {},
    cancelEdit() {},
    saveReply() {},
    generateReply() {},
    ignoreAndArchive() {},
    isGeneratingMessage() {
      return false;
    },
    isSendingMessage() {
      return false;
    },
    research() {},
    togglePromising() {},
    get sortedAndFilteredCompanies() {
      return [];
    },
  };
}

function createMinimalDailyDashboard() {
  return {
    doResearch: false,
    scanningEmails: false,
    emailScanStatus: null,
    loading: false,
    unprocessedMessages: [],
    init() {},
    getSortButtonText() {
      return "Sort Oldest First";
    },
    toggleSortOrder() {},
    refresh() {},
    scanRecruiterEmails() {},
    getEmailScanStatusText() {
      return "";
    },
    getEmailScanStatusClass() {
      return "";
    },
    getFilterHeading() {
      return "Messages (0)";
    },
    get sortedMessages() {
      return [];
    },
    getMessageSender() {
      return "";
    },
    getMessageSubject() {
      return "";
    },
    getMessageDate() {
      return null;
    },
    getCompanyName() {
      return "";
    },
    getMessagePreview() {
      return "";
    },
    toggleMessageExpansion() {},
    getExpandButtonText() {
      return "Show More";
    },
    isResearching() {
      return false;
    },
    getResearchStatusText() {
      return "";
    },
    getResearchStatusClass() {
      return "";
    },
    generateReply() {},
    toggleReplyExpansion() {},
    getReplyExpandButtonText() {
      return "Show More";
    },
    isGeneratingMessage() {
      return false;
    },
    isSendingMessage() {
      return false;
    },
    sendAndArchive() {},
    archive() {},
  };
}

/**
 * Clean up Alpine.js after tests
 */
export function cleanupAlpine() {
  // Clean up Alpine.js
  if (window.Alpine) {
    delete window.Alpine;
  }

  // Restore real timers
  vi.useRealTimers();

  // Reset Alpine reference
  Alpine = null;
}
