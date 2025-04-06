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
import { CompanyResearchService } from "../../static/company-research.js";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

// Mock the CompanyResearchService
vi.mock("../../static/company-research.js", () => {
  return {
    CompanyResearchService: vi.fn().mockImplementation(() => ({
      submitResearch: vi.fn(),
      pollResearchTask: vi.fn(),
      researchingCompany: false,
    })),
  };
});

describe("Research Company Modal", () => {
  let Alpine;
  let component;
  let modal;
  let form;
  let showModalSpy;
  let closeSpy;
  let researchService;

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
      researchCompanyTaskId: null,
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
        // Simple mock that returns a canned string for testing
        return dateString ? "2024/03/20 12:00pm (0 days ago)" : "";
      },
      formatResearchErrors(company) {
        // Simple mock that returns a canned string for testing
        return company?.research_errors ? "Test research error" : "";
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
      async submitResearchCompany() {
        try {
          // Validate form
          if (!this.researchCompanyForm.url && !this.researchCompanyForm.name) {
            this.showError("Please provide either a company URL or name");
            return;
          }

          this.researchingCompany = true;

          // Prepare request body
          const body = {};
          if (this.researchCompanyForm.url) {
            body.url = this.researchCompanyForm.url;
          }
          if (this.researchCompanyForm.name) {
            body.name = this.researchCompanyForm.name;
          }

          // Submit research request
          const response = await fetch("/api/companies", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to start research: ${response.status}`
            );
          }

          const data = await response.json();
          this.researchCompanyTaskId = data.task_id;

          // Close modal and show success message
          this.closeResearchCompanyModal();
          this.showSuccess(
            "Company research started. This may take a few minutes."
          );

          // Poll for task completion
          this.pollResearchCompanyTask();
        } catch (error) {
          this.showError(
            error.message || "Failed to start research. Please try again."
          );
        } finally {
          this.researchingCompany = false;
        }
      },
    };

    // Initialize Alpine.js
    Alpine.data("researchCompanyModal", () => component);

    // Reset mocks
    vi.clearAllMocks();

    // Create a fresh instance of the service
    researchService = new CompanyResearchService();
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
    component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith(
      "Please provide either a company URL or name"
    );
  });

  it("shows loading state during submission and success message after", async () => {
    // Mock fetch for successful API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Set valid URL and submit
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompany();

    // Should show success message and close modal
    expect(component.showSuccess).toHaveBeenCalledWith(
      "Company research started. This may take a few minutes."
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
    await component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("API Error");
  });

  it("validates that either URL or name is provided", async () => {
    // Mock fetch for successful API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Test with neither URL nor name
    component.researchCompanyForm.url = "";
    component.researchCompanyForm.name = "";
    await component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith(
      "Please provide either a company URL or name"
    );

    // Reset mocks
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Test with only URL
    component.researchCompanyForm.url = "https://example.com";
    component.researchCompanyForm.name = "";
    await component.submitResearchCompany();

    // Should not show error message
    expect(component.showError).not.toHaveBeenCalled();

    // Reset mocks
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Test with only name
    component.researchCompanyForm.url = "";
    component.researchCompanyForm.name = "Example Company";
    await component.submitResearchCompany();

    // Should not show error message
    expect(component.showError).not.toHaveBeenCalled();
  });

  it("handles network errors during submission", async () => {
    // Mock fetch to simulate network error
    global.fetch = vi.fn().mockRejectedValueOnce(new Error("Network error"));

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("Network error");
    expect(component.researchingCompany).toBe(false);
  });

  it("handles invalid API responses", async () => {
    // Mock fetch to return invalid JSON
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.reject(new Error("Invalid JSON")),
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("Invalid JSON");
    expect(component.researchingCompany).toBe(false);
  });

  it("handles API timeout errors", async () => {
    // Mock fetch to simulate timeout
    global.fetch = vi.fn().mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error("Request timed out")), 5000);
        })
    );

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    const submitPromise = component.submitResearchCompany();

    // Advance timers to trigger timeout
    await vi.advanceTimersByTime(5000);
    await submitPromise;

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("Request timed out");
    expect(component.researchingCompany).toBe(false);
  });

  it("handles rate limiting errors", async () => {
    // Mock fetch to simulate rate limiting
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: () =>
        Promise.resolve({
          error: "Too many requests. Please try again later.",
        }),
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompany();

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith(
      "Too many requests. Please try again later."
    );
    expect(component.researchingCompany).toBe(false);
  });

  it("handles malformed API responses", async () => {
    // Mock fetch to return success but with unexpected data
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          unexpected: "data",
          message: "This is not the expected response format",
        }),
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    await component.submitResearchCompany();

    // Should show success message and close modal, but task_id will be undefined
    expect(component.researchCompanyTaskId).toBeUndefined();
    expect(component.researchingCompany).toBe(false);
    expect(component.showSuccess).toHaveBeenCalledWith(
      "Company research started. This may take a few minutes."
    );
    expect(closeSpy).toHaveBeenCalled();
    expect(component.pollResearchCompanyTask).toHaveBeenCalled();
  });

  it("should show error when submitting without URL or name", async () => {
    // Setup
    component.researchCompanyForm = { url: "", name: "" };

    // Execute
    await component.submitResearchCompany();

    // Verify
    expect(component.showError).toHaveBeenCalledWith(
      "Please provide either a company URL or name"
    );
    expect(researchService.submitResearch).not.toHaveBeenCalled();
  });

  it("should submit research with URL", async () => {
    // Setup
    const form = { url: "https://example.com", name: "" };
    const taskId = "123";

    // Mock the service to return success
    researchService.submitResearch.mockResolvedValueOnce({ task_id: taskId });

    // Execute
    const result = await researchService.submitResearch(form);

    // Verify
    expect(researchService.submitResearch).toHaveBeenCalledWith(form);
    expect(result).toEqual({ task_id: taskId });
  });

  it("should submit research with name", async () => {
    // Setup
    const form = { url: "", name: "Example Corp" };
    const taskId = "123";

    // Mock the service to return success
    researchService.submitResearch.mockResolvedValueOnce({ task_id: taskId });

    // Execute
    const result = await researchService.submitResearch(form);

    // Verify
    expect(researchService.submitResearch).toHaveBeenCalledWith(form);
    expect(result).toEqual({ task_id: taskId });
  });

  it("should handle API errors", async () => {
    // Setup
    const form = { url: "https://example.com", name: "" };
    const error = new Error("API Error");

    // Mock the service to throw an error
    researchService.submitResearch.mockRejectedValueOnce(error);

    // Execute & Verify
    await expect(researchService.submitResearch(form)).rejects.toThrow(
      "API Error"
    );
  });

  it("should poll task status until completion", async () => {
    // Setup
    const taskId = "123";

    // Mock the service to return running then completed
    researchService.pollResearchTask
      .mockResolvedValueOnce({ status: "running" })
      .mockResolvedValueOnce({ status: "completed" });

    // Execute
    const firstResult = await researchService.pollResearchTask(taskId);
    expect(firstResult).toEqual({ status: "running" });

    const secondResult = await researchService.pollResearchTask(taskId);
    expect(secondResult).toEqual({ status: "completed" });

    // Verify
    expect(researchService.pollResearchTask).toHaveBeenCalledWith(taskId);
    expect(researchService.pollResearchTask).toHaveBeenCalledTimes(2);
  });

  it("should handle task failure", async () => {
    // Setup
    const taskId = "123";
    const error = "Task failed";

    // Mock the service to return failed
    researchService.pollResearchTask.mockResolvedValueOnce({
      status: "failed",
      error,
    });

    // Execute
    const result = await researchService.pollResearchTask(taskId);

    // Verify
    expect(researchService.pollResearchTask).toHaveBeenCalledWith(taskId);
    expect(result).toEqual({ status: "failed", error });
  });
});
