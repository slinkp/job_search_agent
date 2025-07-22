import { beforeEach, describe, expect, it, vi } from "vitest";
import { TaskPollingService } from "../../static/task-polling.js";

// Mock fetch globally
global.fetch = vi.fn();

describe("TaskPollingService", () => {
  let service;

  beforeEach(() => {
    service = new TaskPollingService();
    vi.clearAllMocks();
  });

  describe("constructor", () => {
    it("initializes with empty tracking sets", () => {
      expect(service.researchingCompanies).toBeInstanceOf(Set);
      expect(service.generatingMessages).toBeInstanceOf(Set);
      expect(service.researchingCompanies.size).toBe(0);
      expect(service.generatingMessages.size).toBe(0);
    });
  });

  describe("tracking methods", () => {
    it("adds and removes companies from researching set", () => {
      const company = { name: "Test Company" };

      expect(service.isResearching(company)).toBe(false);

      service.addResearching(company);
      expect(service.isResearching(company)).toBe(true);

      service.removeResearching(company);
      expect(service.isResearching(company)).toBe(false);
    });

    it("adds and removes companies from generating messages set", () => {
      const company = { name: "Test Company" };

      expect(service.isGeneratingMessage(company)).toBe(false);

      service.addGeneratingMessage(company);
      expect(service.isGeneratingMessage(company)).toBe(true);

      service.removeGeneratingMessage(company);
      expect(service.isGeneratingMessage(company)).toBe(false);
    });

    it("handles null company in isGeneratingMessage", () => {
      expect(service.isGeneratingMessage(null)).toBe(false);
    });
  });

  describe("getTaskStatusText", () => {
    it("returns correct text for research status", () => {
      const company = { research_status: "pending" };
      expect(service.getResearchStatusText(company)).toBe(
        "Starting research..."
      );

      company.research_status = "running";
      expect(service.getResearchStatusText(company)).toBe(
        "Researching company..."
      );

      company.research_status = "completed";
      expect(service.getResearchStatusText(company)).toBe("Research complete");

      company.research_status = "failed";
      expect(service.getResearchStatusText(company)).toBe(
        "Failed to research company"
      );
    });

    it("returns correct text for message status", () => {
      const company = { message_status: "pending" };
      expect(service.getMessageStatusText(company)).toBe("Generating reply...");

      company.message_status = "running";
      expect(service.getMessageStatusText(company)).toBe("Generating reply...");

      company.message_status = "completed";
      expect(service.getMessageStatusText(company)).toBe("Reply generated");

      company.message_status = "failed";
      expect(service.getMessageStatusText(company)).toBe(
        "Failed to generate reply"
      );
    });

    it("shows error message when error is present", () => {
      const company = {
        research_status: "failed",
        research_error: "API timeout",
      };
      expect(service.getResearchStatusText(company)).toBe(
        "Failed: API timeout"
      );

      const company2 = {
        message_status: "failed",
        message_error: "Network error",
      };
      expect(service.getMessageStatusText(company2)).toBe(
        "Failed: Network error"
      );
    });

    it("returns empty string for unknown status", () => {
      const company = { research_status: "unknown" };
      expect(service.getResearchStatusText(company)).toBe("");
    });
  });

  describe("getResearchStatusClass", () => {
    it("returns correct CSS classes for research status", () => {
      const company = { research_status: "pending" };
      const classes = service.getResearchStatusClass(company);
      expect(classes["status-pending"]).toBe(true);
      expect(classes["status-running"]).toBe(false);
      expect(classes["status-completed"]).toBe(false);
      expect(classes["status-failed"]).toBe(false);

      company.research_status = "running";
      const classes2 = service.getResearchStatusClass(company);
      expect(classes2["status-running"]).toBe(true);

      company.research_status = "completed";
      const classes3 = service.getResearchStatusClass(company);
      expect(classes3["status-completed"]).toBe(true);

      company.research_status = "failed";
      const classes4 = service.getResearchStatusClass(company);
      expect(classes4["status-failed"]).toBe(true);
    });

    it("shows failed class when error is present", () => {
      const company = {
        research_status: "completed",
        research_error: "Some error",
      };
      const classes = service.getResearchStatusClass(company);
      expect(classes["status-failed"]).toBe(true);
    });
  });

  describe("getMessageStatusClass", () => {
    it("returns correct CSS classes for message status", () => {
      const company = { message_status: "pending" };
      const classes = service.getMessageStatusClass(company);
      expect(classes["status-pending"]).toBe(true);
      expect(classes["status-running"]).toBe(false);
      expect(classes["status-completed"]).toBe(false);
      expect(classes["status-failed"]).toBe(false);

      company.message_status = "running";
      const classes2 = service.getMessageStatusClass(company);
      expect(classes2["status-running"]).toBe(true);

      company.message_status = "completed";
      const classes3 = service.getMessageStatusClass(company);
      expect(classes3["status-completed"]).toBe(true);

      company.message_status = "failed";
      const classes4 = service.getMessageStatusClass(company);
      expect(classes4["status-failed"]).toBe(true);
    });

    it("shows failed class when error is present", () => {
      const company = {
        message_status: "completed",
        message_error: "Some error",
      };
      const classes = service.getMessageStatusClass(company);
      expect(classes["status-failed"]).toBe(true);
    });
  });

  describe("pollTaskStatus", () => {
    it("polls research task status correctly", async () => {
      const company = {
        name: "Test Company",
        research_task_id: "task-123",
        research_status: "pending",
      };

      service.addResearching(company);

      // Mock successful completion
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "completed" }),
      });

      await service.pollResearchStatus(company);

      expect(global.fetch).toHaveBeenCalledWith("/api/tasks/task-123");
      expect(company.research_status).toBe("completed");
      expect(service.isResearching(company)).toBe(false);
    });

    it("polls message task status correctly", async () => {
      const company = {
        name: "Test Company",
        message_task_id: "task-456",
        message_status: "pending",
      };

      service.addGeneratingMessage(company);

      // Mock successful completion
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "completed" }),
      });

      await service.pollMessageStatus(company);

      expect(global.fetch).toHaveBeenCalledWith("/api/tasks/task-456");
      expect(company.message_status).toBe("completed");
      expect(service.isGeneratingMessage(company)).toBe(false);
    });

    it("handles task failure", async () => {
      const company = {
        name: "Test Company",
        research_task_id: "task-123",
        research_status: "running",
      };

      service.addResearching(company);

      // Mock failure
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "failed",
            error: "API timeout",
          }),
      });

      await service.pollResearchStatus(company);

      expect(company.research_status).toBe("failed");
      expect(company.research_error).toBe("API timeout");
      expect(service.isResearching(company)).toBe(false);
    });

    it("handles network errors", async () => {
      const company = {
        name: "Test Company",
        research_task_id: "task-123",
        research_status: "running",
      };

      service.addResearching(company);

      // Mock network error
      global.fetch.mockRejectedValueOnce(new Error("Network error"));

      await service.pollResearchStatus(company);

      expect(service.isResearching(company)).toBe(false);
    });
  });

  describe("reset", () => {
    it("clears all tracking sets", () => {
      const company = { name: "Test Company" };

      service.addResearching(company);
      service.addGeneratingMessage(company);

      expect(service.isResearching(company)).toBe(true);
      expect(service.isGeneratingMessage(company)).toBe(true);

      service.reset();

      expect(service.isResearching(company)).toBe(false);
      expect(service.isGeneratingMessage(company)).toBe(false);
    });
  });
});
