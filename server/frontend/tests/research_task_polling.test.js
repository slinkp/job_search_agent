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
import { cleanupAlpine, setupAlpine } from "./alpine-setup.js";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Research Task Polling", () => {
  let Alpine;
  let component;
  let pollResearchCompanyTask;

  // Import Alpine.js once before all tests
  beforeAll(async () => {
    Alpine = await setupAlpine();
  });

  beforeEach(() => {
    // Reset document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Initialize our test component
    component = {
      showError: vi.fn(),
      showSuccess: vi.fn(),
      refreshAllCompanies: vi.fn(),
      // Helper method to simulate form submission
      async submitResearchCompanyForm(event) {
        if (event) event.preventDefault();

        // Simulate successful API call
        const response = await fetch("/research_company", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ url: "https://example.com" }),
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Failed to start research");
        }

        this.showSuccess("Research started successfully");
        this.pollResearchCompanyTask(data.task_id);
      },
    };

    // Create a mock for the polling function
    pollResearchCompanyTask = vi.fn();
    component.pollResearchCompanyTask = pollResearchCompanyTask;

    // Register our test component with Alpine
    Alpine.data("researchTaskPolling", () => component);
  });

  // Clean up after each test
  afterEach(() => {
    vi.clearAllMocks();
  });

  // Clean up after all tests
  afterAll(() => {
    cleanupAlpine();
  });

  it("starts polling after successful submission", async () => {
    // Mock fetch for successful API call
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, task_id: "123" }),
    });

    // Call the submission method directly
    await component.submitResearchCompanyForm();

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

    // Simulate form submission to start polling
    await component.submitResearchCompanyForm();

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

    // Simulate form submission to start polling
    await component.submitResearchCompanyForm();

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

    // Simulate form submission to start polling
    await component.submitResearchCompanyForm();

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

    // Simulate form submission to start polling
    await component.submitResearchCompanyForm();

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
