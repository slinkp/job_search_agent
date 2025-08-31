import { beforeEach, describe, expect, it, vi } from "vitest";
import { CompaniesService } from "../../static/companies-service.js";

describe("CompaniesService", () => {
  let service;
  beforeEach(() => {
    service = new CompaniesService();
    global.fetch = vi.fn();
  });

  describe("getCompanies", () => {
    it("fetches companies without include_all parameter", async () => {
      const mockCompanies = [{ id: 1, name: "Test Company" }];
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanies),
      });

      const result = await service.getCompanies();
      expect(fetch).toHaveBeenCalledWith("/api/companies");
      expect(result).toEqual(mockCompanies);
    });

    it("fetches companies with include_all parameter", async () => {
      const mockCompanies = [{ id: 1, name: "Test Company" }];
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanies),
      });

      const result = await service.getCompanies(true);
      expect(fetch).toHaveBeenCalledWith("/api/companies?include_all=true");
      expect(result).toEqual(mockCompanies);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(service.getCompanies()).rejects.toThrow(
        "Failed to fetch companies: 500"
      );
    });
  });

  describe("getCompany", () => {
    it("fetches a single company", async () => {
      const mockCompany = { id: 1, name: "Test Company" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompany),
      });

      const result = await service.getCompany("test-id");
      expect(fetch).toHaveBeenCalledWith("/api/companies/test-id");
      expect(result).toEqual(mockCompany);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(service.getCompany("test-id")).rejects.toThrow(
        "Failed to load company: 404"
      );
    });
  });

  describe("updateCompanyDetails", () => {
    it("updates company details", async () => {
      const mockResponse = { success: true };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const payload = { promising: true };
      const result = await service.updateCompanyDetails("test-id", payload);
      expect(fetch).toHaveBeenCalledWith("/api/companies/test-id/details", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
      });

      await expect(
        service.updateCompanyDetails("test-id", {})
      ).rejects.toThrow("Failed to update company details: 400");
    });
  });

  describe("saveReply", () => {
    it("saves a reply message", async () => {
      const mockResponse = { success: true };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.saveReply("message-id", "Reply text");
      expect(fetch).toHaveBeenCalledWith("/api/messages/message-id/reply", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: "Reply text" }),
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Invalid message" }),
      });

      await expect(service.saveReply("message-id", "text")).rejects.toThrow(
        "Invalid message"
      );
    });
  });

  describe("loadCompany", () => {
    it("loads company with associated messages", async () => {
      const mockCompany = { id: 1, name: "Test Company" };
      const mockMessages = [
        { message_id: 1, company_id: "test-id", content: "Message 1" },
        { message_id: 2, company_id: "other-id", content: "Message 2" },
      ];

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockCompany),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockMessages),
        });

      const result = await service.loadCompany("test-id");
      expect(fetch).toHaveBeenCalledWith("/api/companies/test-id");
      expect(fetch).toHaveBeenCalledWith("/api/messages");
      expect(result).toEqual({
        ...mockCompany,
        associated_messages: [mockMessages[0]],
      });
    });

    it("loads company without messages when messages request fails", async () => {
      const mockCompany = { id: 1, name: "Test Company" };

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockCompany),
        })
        .mockResolvedValueOnce({
          ok: false,
        });

      const result = await service.loadCompany("test-id");
      expect(result).toEqual({
        ...mockCompany,
        associated_messages: [],
      });
    });
  });

  describe("loadMessageAndCompany", () => {
    it("loads message and associated company", async () => {
      const mockMessages = [
        { message_id: "msg-1", company_id: "company-1", content: "Message 1" },
        { message_id: "msg-2", company_id: "company-2", content: "Message 2" },
      ];
      const mockCompany = { id: "company-1", name: "Test Company" };

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockMessages),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockCompany),
        });

      const result = await service.loadMessageAndCompany("msg-1");
      expect(fetch).toHaveBeenCalledWith("/api/messages");
      expect(fetch).toHaveBeenCalledWith("/api/companies/company-1");
      expect(result).toEqual({
        company: {
          ...mockCompany,
          associated_messages: [mockMessages[0]],
        },
        message: mockMessages[0],
      });
    });

    it("throws error when messages request fails", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(service.loadMessageAndCompany("msg-1")).rejects.toThrow(
        "Failed to load messages: 500"
      );
    });

    it("throws error when message not found", async () => {
      const mockMessages = [
        { message_id: "msg-2", company_id: "company-2", content: "Message 2" },
      ];

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMessages),
      });

      await expect(service.loadMessageAndCompany("msg-1")).rejects.toThrow(
        "Message not found"
      );
    });
  });

  describe("archiveMessage", () => {
    it("archives a message", async () => {
      const mockResponse = { success: true };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.archiveMessage("message-id");
      expect(fetch).toHaveBeenCalledWith("/api/messages/message-id/archive", {
        method: "POST",
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Message not found" }),
      });

      await expect(service.archiveMessage("message-id")).rejects.toThrow(
        "Message not found"
      );
    });
  });

  describe("sendAndArchive", () => {
    it("sends and archives a message", async () => {
      const mockResponse = { success: true };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.sendAndArchive("message-id");
      expect(fetch).toHaveBeenCalledWith("/api/messages/message-id/send_and_archive", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Invalid message" }),
      });

      await expect(service.sendAndArchive("message-id")).rejects.toThrow(
        "Invalid message"
      );
    });
  });

  describe("generateReply", () => {
    it("generates a reply for a message", async () => {
      const mockResponse = { task_id: "task-123", status: "pending" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.generateReply("message-id");
      expect(fetch).toHaveBeenCalledWith("/api/messages/message-id/reply", {
        method: "POST",
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Invalid message" }),
      });

      await expect(service.generateReply("message-id")).rejects.toThrow(
        "Invalid message"
      );
    });
  });

  describe("research", () => {
    it("starts research for a company", async () => {
      const mockResponse = { task_id: "task-123", status: "pending" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.research("company-id");
      expect(fetch).toHaveBeenCalledWith("/api/companies/company-id/research", {
        method: "POST",
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Company not found" }),
      });

      await expect(service.research("company-id")).rejects.toThrow(
        "Company not found"
      );
    });
  });

  describe("importCompanies", () => {
    it("starts import companies process", async () => {
      const mockResponse = { task_id: "task-123" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.importCompanies();
      expect(fetch).toHaveBeenCalledWith("/api/import_companies", {
        method: "POST",
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
        json: () => Promise.resolve({ error: "Import failed" }),
      });

      await expect(service.importCompanies()).rejects.toThrow(
        "Import failed"
      );
    });
  });

  describe("submitResearch", () => {
    it("submits research data", async () => {
      const mockResponse = { task_id: "task-123" };
      const researchData = { url: "http://example.com", name: "Test Company" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.submitResearch(researchData);
      expect(fetch).toHaveBeenCalledWith("/api/companies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(researchData),
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      const researchData = { url: "http://example.com" };
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Invalid URL" }),
      });

      await expect(service.submitResearch(researchData)).rejects.toThrow(
        "Invalid URL"
      );
    });
  });

  describe("pollResearchTask", () => {
    it("polls research task status", async () => {
      const mockResponse = { status: "completed", result: { company_id: "123" } };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.pollResearchTask("task-123");
      expect(fetch).toHaveBeenCalledWith("/api/tasks/task-123");
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(service.pollResearchTask("task-123")).rejects.toThrow(
        "Failed to poll research task: 404"
      );
    });
  });

  describe("pollTask", () => {
    it("polls task status", async () => {
      const mockResponse = { status: "completed", result: { success: true } };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.pollTask("task-123");
      expect(fetch).toHaveBeenCalledWith("/api/tasks/task-123");
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(service.pollTask("task-123")).rejects.toThrow(
        "Failed to poll task: 404"
      );
    });
  });

  describe("scanEmails", () => {
    it("scans emails with default max messages", async () => {
      const mockResponse = { task_id: "task-123", status: "pending" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.scanEmails();
      expect(fetch).toHaveBeenCalledWith("/api/scan_emails", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ max_messages: 10 }),
      });
      expect(result).toEqual(mockResponse);
    });

    it("scans emails with custom max messages", async () => {
      const mockResponse = { task_id: "task-123", status: "pending" };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await service.scanEmails(20);
      expect(fetch).toHaveBeenCalledWith("/api/scan_emails", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ max_messages: 20 }),
      });
      expect(result).toEqual(mockResponse);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: "Scan failed" }),
      });

      await expect(service.scanEmails()).rejects.toThrow(
        "Scan failed"
      );
    });
  });

  describe("getMessages", () => {
    it("fetches messages", async () => {
      const mockMessages = [
        { message_id: "msg-1", company_id: "company-1", content: "Message 1" },
        { message_id: "msg-2", company_id: "company-2", content: "Message 2" },
      ];
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMessages),
      });

      const result = await service.getMessages();
      expect(fetch).toHaveBeenCalledWith("/api/messages");
      expect(result).toEqual(mockMessages);
    });

    it("throws error on failed request", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(service.getMessages()).rejects.toThrow(
        "Failed to load messages: 500"
      );
    });
  });

  describe("merge and duplicates", () => {
    it("starts merge task", async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ task_id: "t1", status: "pending" }),
      });

      const result = await service.mergeCompanies("canon", "dup");
      expect(fetch).toHaveBeenCalledWith(
        "/api/companies/canon/merge",
        expect.objectContaining({ method: "POST" })
      );
      expect(result.task_id).toBe("t1");
    });

    it("loads potential duplicates", async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(["a", "b"]),
      });

      const result = await service.getPotentialDuplicates("canon");
      expect(fetch).toHaveBeenCalledWith(
        "/api/companies/canon/potential-duplicates"
      );
      expect(result).toEqual(["a", "b"]);
    });
  });
});


