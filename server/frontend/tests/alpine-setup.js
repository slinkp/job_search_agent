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

    // Register core components that exist in the real application
    Alpine.data("companyList", () => createMockCompanyList());
    Alpine.data("dailyDashboard", () => createMockDailyDashboard());
  }

  // Disable Alpine's warning system to prevent unhandled errors
  Alpine.onWarning = () => {};

  try {
    // Start Alpine (initialize)
    Alpine.start();
  } catch (err) {
    console.warn(
      "Alpine initialization warning (safe to ignore):",
      err.message
    );
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
 * Create a basic mock of the dailyDashboard component
 */
function createMockDailyDashboard() {
  return {
    unprocessedMessages: [],
    loading: false,
    sortNewestFirst: true,
    doResearch: false, // Add the missing doResearch property
    init() {
      console.log("Mock dailyDashboard initialized");
    },
    loadUnprocessedMessages() {
      // Stub method
    },
    formatMessageDate() {
      return "";
    },
    getCompanyName() {
      return "";
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
    refresh() {
      // Stub method
    },
    toggleSortOrder() {
      // Stub method
    },
    getSortButtonText() {
      return "Newest First";
    },
    get sortedMessages() {
      return [];
    },
  };
}

/**
 * Create a basic mock of the companyList component
 */
function createMockCompanyList() {
  return {
    companies: [],
    loading: false,
    editingCompany: null,
    editingReply: "",
    researchingCompanies: new Set(),
    generatingMessages: new Set(),
    scanningEmails: false,
    emailScanTaskId: null,
    emailScanStatus: null,
    emailScanError: null,
    importingCompanies: false,
    importTaskId: null,
    importStatus: null,
    importError: null,
    sortField: "name",
    sortAsc: true,
    filterMode: "all",
    researchCompanyModalOpen: false,
    researchingCompany: false,
    researchCompanyForm: {
      url: "",
      name: "",
    },
    researchCompanyTaskId: null,
    // View mode toggle functionality
    viewMode: "company_management",
    init() {
      console.log("Mock companyList initialized");
    },
    showError() {},
    showSuccess() {},
    // View mode methods
    toggleViewMode() {
      this.viewMode =
        this.viewMode === "company_management"
          ? "daily_dashboard"
          : "company_management";
    },
    isCompanyManagementView() {
      return this.viewMode === "company_management";
    },
    isDailyDashboardView() {
      return this.viewMode === "daily_dashboard";
    },
    isResearching() {
      return false;
    },
    isGeneratingMessage() {
      return false;
    },
    formatRecruiterMessageDate() {
      return "";
    },
    formatResearchErrors() {
      return "";
    },
    getResearchStatusText() {
      return "";
    },
    getResearchStatusClass() {
      return {};
    },
    getMessageStatusText() {
      return "";
    },
    getEmailScanStatusText() {
      return "";
    },
    getEmailScanStatusClass() {
      return {};
    },
    importCompaniesFromSpreadsheet() {
      // Stub method
      console.log("Import companies stub called");
    },
    get filteredCompanies() {
      return [];
    },
    get sortedAndFilteredCompanies() {
      return [];
    },
    // Any other methods that might be accessed in the HTML
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

  // Mock HTML element methods that Alpine.js might use
  if (!HTMLElement.prototype._x_forceModelUpdate) {
    HTMLElement.prototype._x_forceModelUpdate = () => {};
  }

  // Add any missing element methods used by Alpine
  ["selectionStart", "selectionEnd", "setSelectionRange"].forEach((prop) => {
    if (!(prop in HTMLTextAreaElement.prototype)) {
      Object.defineProperty(HTMLTextAreaElement.prototype, prop, {
        configurable: true,
        get() {
          return 0;
        },
        set() {},
      });
    }
  });

  // Mock element.scrollIntoView()
  if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = () => {};
  }
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
