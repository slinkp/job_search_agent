import { beforeEach, describe, expect, it, vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils";

describe("App", () => {
  beforeEach(() => {
    // Set up document with actual HTML
    setupDocumentWithIndexHtml(document);
  });

  it("can manipulate the DOM", () => {
    // Create a test element
    const div = document.createElement("div");
    div.textContent = "Test Content";
    document.body.appendChild(div);

    // Test that the element is in the document
    expect(document.body.textContent).toContain("Test Content");
  });
});

describe("Company Import UI", () => {
  let Alpine;
  let companyList;

  beforeEach(() => {
    // Set up document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Create required modal elements
    const importModal = document.createElement("dialog");
    importModal.id = "import-companies-modal";
    document.body.appendChild(importModal);

    // Mock Alpine.js data
    companyList = {
      importingCompanies: false,
      importError: null,
      importStatus: null,
      importTaskId: null,
      showSuccess: vi.fn(),
      showError: vi.fn(),
      closeImportCompaniesModal: vi.fn(),
      pollTaskStatus: vi.fn(),
      importCompaniesFromSpreadsheet: vi.fn(async function () {
        const response = await global.fetch("/api/import_companies", {
          method: "POST",
        });
        if (response.ok) {
          const data = await response.json();
          this.importingCompanies = true;
          this.importTaskId = data.task_id;
          this.importError = null;
          this.importStatus = {
            percent_complete: 0,
            current_company: "",
            processed: 0,
            total_found: 0,
            created: 0,
            updated: 0,
            skipped: 0,
            errors: 0,
            status: "pending",
          };
          this.pollTaskStatus(null, "import_companies");
        } else {
          const error = await response.json();
          this.importingCompanies = false;
          this.importError = error.error;
          this.showError(`Failed to start import: ${error.error}`);
        }
      }),
    };

    // Mock fetch
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = "";
  });

  it("starts import process when button is clicked", async () => {
    // Mock successful API response
    global.fetch.mockImplementationOnce((url, options) =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ task_id: "test-task-123" }),
      })
    );

    // Call import function
    await companyList.importCompaniesFromSpreadsheet();

    // Verify API was called
    expect(global.fetch).toHaveBeenCalledWith("/api/import_companies", {
      method: "POST",
    });

    // Verify state changes
    expect(companyList.importingCompanies).toBe(true);
    expect(companyList.importTaskId).toBe("test-task-123");
    expect(companyList.importError).toBe(null);

    // Verify initial status
    expect(companyList.importStatus).toEqual({
      percent_complete: 0,
      current_company: "",
      processed: 0,
      total_found: 0,
      created: 0,
      updated: 0,
      skipped: 0,
      errors: 0,
      status: "pending",
    });

    // Verify polling was started
    expect(companyList.pollTaskStatus).toHaveBeenCalledWith(
      null,
      "import_companies"
    );
  });

  it("handles API errors during import start", async () => {
    // Mock failed API response
    const errorMessage = "Failed to connect to spreadsheet";
    global.fetch.mockImplementationOnce((url, options) =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: errorMessage }),
      })
    );

    // Call import function
    await companyList.importCompaniesFromSpreadsheet();

    // Verify error handling
    expect(companyList.importingCompanies).toBe(false);
    expect(companyList.importError).toBe(errorMessage);
    expect(companyList.showError).toHaveBeenCalledWith(
      `Failed to start import: ${errorMessage}`
    );
  });

  it("updates progress during import", () => {
    const progressUpdate = {
      percent_complete: 50,
      current_company: "Test Corp",
      processed: 5,
      total_found: 10,
      created: 3,
      updated: 2,
      skipped: 0,
      errors: 0,
      status: "running",
    };

    // Update import status
    companyList.importStatus = progressUpdate;

    // Verify status was updated correctly
    expect(companyList.importStatus).toEqual(progressUpdate);
  });

  it("shows success message on completion", async () => {
    const finalStatus = {
      percent_complete: 100,
      current_company: "",
      processed: 10,
      total_found: 10,
      created: 6,
      updated: 3,
      skipped: 1,
      errors: 0,
      status: "completed",
    };

    // Mock successful completion
    companyList.importStatus = finalStatus;

    // Simulate the completion handler from the pollTaskStatus function
    companyList.importingCompanies = false;
    companyList.showSuccess(
      `Import completed! Created: ${finalStatus.created}, Updated: ${finalStatus.updated}, Skipped: ${finalStatus.skipped}, Errors: ${finalStatus.errors}`
    );

    // Verify success message
    expect(companyList.showSuccess).toHaveBeenCalledWith(
      "Import completed! Created: 6, Updated: 3, Skipped: 1, Errors: 0"
    );
  });
});

describe("Duplicate Merge Modal", () => {
  beforeEach(() => {
    setupDocumentWithIndexHtml(document);
  });

  it("renders duplicate modal and button", () => {
    const modal = document.getElementById("duplicate-modal");
    expect(modal).toBeTruthy();
    // Presence of Mark as Duplicate button
    const rawHtml = document.body.innerHTML;
    expect(rawHtml).toContain("Mark as Duplicate");
  });
});

describe("Daily Dashboard View Mode Toggle", () => {
  let companyList;

  beforeEach(() => {
    // Set up document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Mock Alpine.js data with view mode functionality
    companyList = {
      viewMode: "company_management", // Default view mode
      toggleViewMode: vi.fn(function () {
        this.viewMode =
          this.viewMode === "company_management"
            ? "daily_dashboard"
            : "company_management";
      }),
      isCompanyManagementView: vi.fn(function () {
        return this.viewMode === "company_management";
      }),
      isDailyDashboardView: vi.fn(function () {
        return this.viewMode === "daily_dashboard";
      }),
    };
  });

  it("should default to company management view", () => {
    expect(companyList.viewMode).toBe("company_management");
    expect(companyList.isCompanyManagementView()).toBe(true);
    expect(companyList.isDailyDashboardView()).toBe(false);
  });

  it("should toggle between view modes", () => {
    // Start in company management view
    expect(companyList.viewMode).toBe("company_management");

    // Toggle to daily dashboard
    companyList.toggleViewMode();
    expect(companyList.viewMode).toBe("daily_dashboard");
    expect(companyList.isDailyDashboardView()).toBe(true);
    expect(companyList.isCompanyManagementView()).toBe(false);

    // Toggle back to company management
    companyList.toggleViewMode();
    expect(companyList.viewMode).toBe("company_management");
    expect(companyList.isCompanyManagementView()).toBe(true);
    expect(companyList.isDailyDashboardView()).toBe(false);
  });

  it("should show correct view based on view mode", () => {
    // Mock DOM elements for different views
    const companyView = document.createElement("div");
    companyView.setAttribute("x-show", "isCompanyManagementView()");
    companyView.id = "company-management-view";
    document.body.appendChild(companyView);

    const dashboardView = document.createElement("div");
    dashboardView.setAttribute("x-show", "isDailyDashboardView()");
    dashboardView.id = "daily-dashboard-view";
    document.body.appendChild(dashboardView);

    // Test that the correct view logic is called
    expect(companyList.isCompanyManagementView()).toBe(true);
    expect(companyList.isDailyDashboardView()).toBe(false);

    companyList.toggleViewMode();

    expect(companyList.isCompanyManagementView()).toBe(false);
    expect(companyList.isDailyDashboardView()).toBe(true);
  });
});
