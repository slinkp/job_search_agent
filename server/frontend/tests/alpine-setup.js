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
    doResearch: false,
    hideRepliedMessages: true,
    hideArchivedCompanies: true,
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
      this.sortNewestFirst = !this.sortNewestFirst;
    },
    getSortButtonText() {
      return this.sortNewestFirst ? "Sort Oldest First" : "Sort Newest First";
    },
    scanRecruiterEmails() {
      // Stub method
    },
    toggleHideRepliedMessages() {
      this.hideRepliedMessages = !this.hideRepliedMessages;
    },
    toggleHideArchivedCompanies() {
      this.hideArchivedCompanies = !this.hideArchivedCompanies;
    },
    getRepliedToggleText() {
      return this.hideRepliedMessages ? "Show Replied Messages" : "Hide Replied Messages";
    },
    getArchivedToggleText() {
      return this.hideArchivedCompanies ? "Show Archived Companies" : "Hide Archived Companies";
    },
    getEmailScanStatusText() {
      return this.emailScanStatus || "";
    },
    getEmailScanStatusClass() {
      return "email-scan-status";
    },
    research() {
      // Stub method
    },
    generateReply() {
      // Stub method
    },
    archive() {
      // Stub method
    },
    isResearching() {
      return false;
    },
    isGeneratingMessage() {
      return false;
    },
    getResearchStatusText() {
      return "";
    },
    getResearchStatusClass() {
      return "";
    },
    getMessagePreview() {
      return "";
    },
    toggleMessageExpansion() {
      // Stub method
    },
    getExpandButtonText() {
      return "Expand";
    },
    get sortedMessages() {
      return this.unprocessedMessages; // Return the messages for the template
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
    // Show archived toggle functionality
    showArchived: false,
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
    toggleShowArchived() {
      this.showArchived = !this.showArchived;
    },
    refreshAllCompanies() {
      // Stub method
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
    // Navigation methods to handle the click handlers added to index.html
    navigateToCompany(companyId) {
      // This handles the navigation event dispatching in the HTML
      console.log("Navigating to company:", companyId);
    },
    navigateToMessage(messageId) {
      // This handles the navigation event dispatching in the HTML
      console.log("Navigating to message:", messageId);
    },
    // Research company modal methods
    showResearchCompanyModal() {
      this.researchCompanyModalOpen = true;
    },
    closeResearchCompanyModal() {
      this.researchCompanyModalOpen = false;
      this.researchCompanyForm = { url: "", name: "" };
    },
    submitResearchCompany() {
      this.researchingCompany = true;
      // Simulate async operation
      setTimeout(() => {
        this.researchingCompany = false;
        this.closeResearchCompanyModal();
      }, 100);
    },
    // Import companies modal methods
    showImportCompaniesModal() {
      // Stub method
    },
    closeImportCompaniesModal() {
      // Stub method
    },
    confirmImportCompanies() {
      // Stub method
    },
    // Research methods
    research() {
      // Stub method
    },
    generateReply() {
      // Stub method
    },
    editReply() {
      // Stub method
    },
    saveReply() {
      // Stub method
    },
    cancelEdit() {
      // Stub method
    },
    togglePromising() {
      // Stub method
    },
    toggleSort() {
      // Stub method
    },
    isUrl() {
      return false;
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
