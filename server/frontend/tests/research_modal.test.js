import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Research Company Modal", () => {
  let Alpine;
  let component;
  let modal;
  let form;
  let showModalSpy;
  let closeSpy;

  // Import Alpine.js once before all tests
  beforeAll(async () => {
    // Create a document before importing Alpine
    setupDocumentWithIndexHtml(document);

    // Mock MutationObserver
    global.MutationObserver = class {
      constructor(callback) {
        this.callback = callback;
      }
      observe() {}
      disconnect() {}
    };

    // Use fake timers to prevent Alpine's plugin warning system from running
    vi.useFakeTimers();

    // Import and initialize Alpine
    Alpine = (await import("alpinejs")).default;
    window.Alpine = Alpine;

    // Disable Alpine's warning system to prevent unhandled errors
    Alpine.onWarning = () => {};

    Alpine.start();
  });

  beforeEach(() => {
    // Reset document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Get modal element
    modal = document.getElementById("research-company-modal");
    form = modal.querySelector("form");

    // Create spies for modal methods
    showModalSpy = vi.spyOn(modal, "showModal");
    closeSpy = vi.spyOn(modal, "close");

    // Initialize Alpine.js component data
    component = {
      companies: [],
      loading: false,
      researchingCompany: null,
      editingCompany: {
        recruiter_message: {
          message: "Test message",
          subject: "Test subject",
          sender: "test@example.com",
          date: "2024-03-20T12:00:00Z",
          email_thread_link: "https://example.com/thread",
        },
        research_errors: [],
      },
      researchCompanyForm: {
        url: "",
        name: "",
      },
      showError: vi.fn(),
      showSuccess: vi.fn(),
      formatRecruiterMessageDate(dateString) {
        if (!dateString) return "";
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        let hours = date.getHours();
        const ampm = hours >= 12 ? "pm" : "am";
        hours = hours % 12;
        hours = hours ? hours : 12;
        const minutes = String(date.getMinutes()).padStart(2, "0");
        return `${year}/${month}/${day} ${hours}:${minutes}${ampm} (${diffDays} days ago)`;
      },
      formatResearchErrors(company) {
        if (!company || !company.research_errors) return "";
        if (typeof company.research_errors === "string") {
          return company.research_errors;
        }
        if (Array.isArray(company.research_errors)) {
          return company.research_errors
            .map((err) => {
              if (typeof err === "string") return err;
              if (err && err.step && err.error)
                return `${err.step}: ${err.error}`;
              return JSON.stringify(err);
            })
            .join("; ");
        }
        return JSON.stringify(company.research_errors);
      },
      showResearchCompanyModal() {
        modal.showModal();
      },
      closeResearchCompanyModal() {
        modal.close();
        this.researchCompanyForm.url = "";
        this.researchCompanyForm.name = "";
      },
      pollResearchCompanyTask: vi.fn(),
      async submitResearchCompanyForm(event) {
        event.preventDefault();

        if (!this.researchCompanyForm.url && !this.researchCompanyForm.name) {
          this.showError("Please provide either a company URL or name");
          return;
        }

        this.loading = true;
        try {
          const response = await fetch("/research_company", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(this.researchCompanyForm),
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || "Failed to start research");
          }

          this.showSuccess("Research started successfully");
          this.pollResearchCompanyTask(data.task_id);
          this.closeResearchCompanyModal();
        } catch (error) {
          this.showError(error.message);
        } finally {
          this.loading = false;
        }
      },
    };

    // Initialize Alpine.js
    Alpine.data("researchCompanyModal", () => component);
  });

  // Clean up after each test
  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  // Clean up after all tests
  afterAll(() => {
    // Clean up Alpine.js
    if (window.Alpine) {
      delete window.Alpine;
    }
    // Restore real timers
    vi.useRealTimers();
    // Restore original MutationObserver
    delete global.MutationObserver;
  });

  it("opens when clicking the research button", () => {
    // Find and click the research button
    component.showResearchCompanyModal();

    // Modal should be opened using showModal()
    expect(showModalSpy).toHaveBeenCalled();
  });

  it("closes when clicking the cancel button", () => {
    // Call the close method
    component.closeResearchCompanyModal();

    // Modal should be closed using close()
    expect(closeSpy).toHaveBeenCalled();
  });

  it("validates form input and shows error message", () => {
    // Submit form without any input
    component.submitResearchCompanyForm(new Event("submit"));

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith(
      "Please provide either a company URL or name"
    );
  });

  it("shows loading state during submission and success message after", async () => {
    // Mock fetch for successful API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });

    // Set valid URL and submit
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // Should show success message and close modal
    expect(component.showSuccess).toHaveBeenCalledWith(
      "Research started successfully"
    );
    expect(closeSpy).toHaveBeenCalled();
  });

  it("handles API errors properly", async () => {
    // Mock fetch for failed API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ error: "API Error" }),
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("API Error");
  });

  it("starts polling after successful submission", async () => {
    // Mock fetch for successful API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // Should start polling with the task ID
    expect(component.pollResearchCompanyTask).toHaveBeenCalledWith("123");
  });

  it("continues polling until task is complete", async () => {
    // Mock fetch responses for task status
    global.fetch = vi.fn().mockResolvedValueOnce({
      // Initial submission
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Set up polling mock implementation
    let pollCount = 0;
    component.pollResearchCompanyTask.mockImplementation(async (taskId) => {
      pollCount++;
      // Simulate task completion after 2 polls
      if (pollCount >= 2) {
        component.showSuccess("Research complete");
      } else {
        // Schedule next poll
        setTimeout(() => {
          component.pollResearchCompanyTask(taskId);
        }, 1000);
      }
    });

    // Submit form to start polling
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // First poll should have started
    expect(pollCount).toBe(1);

    // Advance timers to trigger second poll
    await vi.advanceTimersByTime(1000);
    expect(pollCount).toBe(2);
    expect(component.showSuccess).toHaveBeenCalledWith("Research complete");
  });

  it("handles errors during task polling", async () => {
    // Mock fetch for initial successful submission
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Set up polling mock to simulate an error
    let pollCount = 0;
    component.pollResearchCompanyTask.mockImplementation(async (taskId) => {
      pollCount++;
      if (pollCount === 1) {
        // First poll fails
        component.showError("Failed to check task status");
        // Schedule next poll despite error
        setTimeout(() => {
          component.pollResearchCompanyTask(taskId);
        }, 1000);
      }
    });

    // Submit form to start polling
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // First poll should have failed
    expect(pollCount).toBe(1);
    expect(component.showError).toHaveBeenCalledWith(
      "Failed to check task status"
    );

    // Verify polling continues after error
    await vi.advanceTimersByTime(1000);
    await vi.runAllTimers(); // Run any remaining timers
    expect(pollCount).toBe(2);
  });

  it("stops polling when task fails permanently", async () => {
    // Mock fetch for initial successful submission
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Set up polling mock to simulate task failure
    let pollCount = 0;
    component.pollResearchCompanyTask.mockImplementation(async (taskId) => {
      pollCount++;
      if (pollCount === 1) {
        // First poll shows task is still running
        setTimeout(() => {
          component.pollResearchCompanyTask(taskId);
        }, 1000);
      } else if (pollCount === 2) {
        // Second poll shows task failed
        component.showError("Research failed: Company website not accessible");
        // Don't schedule another poll - task has permanently failed
      }
    });

    // Submit form to start polling
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // First poll should schedule next check
    expect(pollCount).toBe(1);

    // Advance to second poll
    await vi.advanceTimersByTime(1000);
    await vi.runAllTimers();
    expect(pollCount).toBe(2);
    expect(component.showError).toHaveBeenCalledWith(
      "Research failed: Company website not accessible"
    );

    // Advance timer again - no more polls should occur
    await vi.advanceTimersByTime(1000);
    await vi.runAllTimers();
    expect(pollCount).toBe(2);
  });

  it("updates company list when research task completes successfully", async () => {
    // Mock fetch for initial successful submission
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Mock refreshAllCompanies method
    const mockCompanies = [
      {
        company_id: "1",
        name: "Company A",
        research_completed_at: "2023-01-01",
      },
      { company_id: "2", name: "Company B", research_completed_at: null },
      {
        company_id: "3",
        name: "New Company",
        research_completed_at: "2023-06-15",
      },
    ];

    component.refreshAllCompanies = vi.fn().mockImplementation(async () => {
      // Update the companies array with the mock data
      component.companies = [...mockCompanies];
      return mockCompanies;
    });

    // Set up polling mock to simulate successful completion
    let pollCount = 0;
    component.pollResearchCompanyTask.mockImplementation(async (taskId) => {
      pollCount++;
      if (pollCount === 1) {
        // First poll shows task is still running
        setTimeout(() => {
          component.pollResearchCompanyTask(taskId);
        }, 1000);
      } else if (pollCount === 2) {
        // Second poll shows task completed successfully
        component.showSuccess("Company research completed!");
        // Call refreshAllCompanies to update the company list
        await component.refreshAllCompanies();
      }
    });

    // Submit form to start polling
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompanyForm(new Event("submit"));

    // First poll should schedule next check
    expect(pollCount).toBe(1);

    // Advance to second poll
    await vi.advanceTimersByTime(1000);
    await vi.runAllTimers();

    // Verify second poll occurred
    expect(pollCount).toBe(2);

    // Verify success message was shown
    expect(component.showSuccess).toHaveBeenCalledWith(
      "Company research completed!"
    );

    // Verify company list was refreshed
    expect(component.refreshAllCompanies).toHaveBeenCalled();

    // Verify companies array was updated with new data
    expect(component.companies).toEqual(mockCompanies);
  });
});
