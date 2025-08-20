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
});


