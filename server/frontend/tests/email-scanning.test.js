import { beforeEach, describe, expect, it, vi } from "vitest";
import { EmailScanningService } from "../../static/email-scanning.js";

// Mock fetch globally
global.fetch = vi.fn();

describe("EmailScanningService", () => {
  let service;

  beforeEach(() => {
    service = new EmailScanningService();
    vi.clearAllMocks();
  });

  describe("constructor", () => {
    it("should initialize with default state", () => {
      expect(service.scanningEmails).toBe(false);
      expect(service.emailScanTaskId).toBe(null);
      expect(service.emailScanStatus).toBe(null);
      expect(service.emailScanError).toBe(null);
    });
  });

  describe("scanRecruiterEmails", () => {
    it("should return early if already scanning", async () => {
      service.scanningEmails = true;
      await service.scanRecruiterEmails();
      expect(fetch).not.toHaveBeenCalled();
    });

    it("should make API call with correct parameters", async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ task_id: "123", status: "pending" }),
      };
      fetch.mockResolvedValue(mockResponse);

      await service.scanRecruiterEmails(true);

      expect(fetch).toHaveBeenCalledWith("/api/scan_recruiter_emails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ do_research: true }),
      });
      expect(service.emailScanTaskId).toBe("123");
      expect(service.emailScanStatus).toBe("pending");
    });

    it("should handle API errors", async () => {
      const mockResponse = {
        ok: false,
        json: vi.fn().mockResolvedValue({ error: "API Error" }),
      };
      fetch.mockResolvedValue(mockResponse);

      await expect(service.scanRecruiterEmails()).rejects.toThrow("API Error");
      expect(service.emailScanError).toBe("API Error");
    });
  });

  describe("getEmailScanStatusText", () => {
    it("should return error message when there is an error", () => {
      service.emailScanError = "Test error";
      expect(service.getEmailScanStatusText()).toBe("Failed: Test error");
    });

    it("should return appropriate status messages", () => {
      const testCases = [
        { status: "pending", expected: "Starting email scan..." },
        {
          status: "running",
          expected:
            "Scanning recruiter emails... (this may take a while for large fetches)",
        },
        { status: "completed", expected: "Email scan complete" },
        { status: "failed", expected: "Failed to scan emails" },
        { status: "unknown", expected: "" },
      ];

      testCases.forEach(({ status, expected }) => {
        service.emailScanStatus = status;
        service.emailScanError = null;
        expect(service.getEmailScanStatusText()).toBe(expected);
      });
    });
  });

  describe("getEmailScanStatusClass", () => {
    it("should return correct CSS classes for each status", () => {
      const testCases = [
        {
          status: "pending",
          expected: {
            "status-pending": true,
            "status-running": false,
            "status-completed": false,
            "status-failed": false,
          },
        },
        {
          status: "running",
          expected: {
            "status-pending": false,
            "status-running": true,
            "status-completed": false,
            "status-failed": false,
          },
        },
        {
          status: "completed",
          expected: {
            "status-pending": false,
            "status-running": false,
            "status-completed": true,
            "status-failed": false,
          },
        },
        {
          status: "failed",
          expected: {
            "status-pending": false,
            "status-running": false,
            "status-completed": false,
            "status-failed": true,
          },
        },
      ];

      testCases.forEach(({ status, expected }) => {
        service.emailScanStatus = status;
        expect(service.getEmailScanStatusClass()).toEqual(expected);
      });
    });
  });

  describe("reset", () => {
    it("should reset all state to initial values", () => {
      service.scanningEmails = true;
      service.emailScanTaskId = "123";
      service.emailScanStatus = "running";
      service.emailScanError = "error";

      service.reset();

      expect(service.scanningEmails).toBe(false);
      expect(service.emailScanTaskId).toBe(null);
      expect(service.emailScanStatus).toBe(null);
      expect(service.emailScanError).toBe(null);
    });
  });
});
