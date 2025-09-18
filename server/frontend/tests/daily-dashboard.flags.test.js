import { describe, it, expect, beforeEach, vi } from "vitest";
import { captureAlpineFactories, loadIndexHtml } from "./test-utils.js";

// Mocks
vi.mock("../../static/task-polling.js", () => ({
  TaskPollingService: class {
    addResearching() {}
    removeResearching() {}
    addGeneratingMessage() {}
    removeGeneratingMessage() {}
    addSendingMessage() {}
    removeSendingMessage() {}
    async pollResearchStatus() {
      return { status: "completed" };
    }
    getResearchStatusText() {
      return "";
    }
    getResearchStatusClass() {
      return "";
    }
    async pollMessageStatus() {
      return { status: "completed" };
    }
    async pollSendAndArchiveStatus() {
      return { status: "completed" };
    }
  },
}));

vi.mock("../../static/ui-utils.js", () => ({
  confirmDialogs: {
    archiveWithoutReply: () => true,
    sendAndArchive: () => true,
  },
  errorLogger: { logFailedTo: () => {}, logError: () => {} },
  showError: () => {},
  showSuccess: () => {},
  formatMessageDate: (d) => String(d || ""),
}));

vi.mock("../../static/email-scanning.js", () => ({
  EmailScanningService: class {
    get scanningEmails() {
      return false;
    }
    get emailScanStatus() {
      return null;
    }
    getEmailScanStatusText() {
      return "";
    }
    getEmailScanStatusClass() {
      return "";
    }
    async scanRecruiterEmails() {
      return {};
    }
    async pollEmailScanStatus() {
      return { status: "completed" };
    }
  },
}));

vi.mock("../../static/url-utils.js", () => ({
  readDailyDashboardStateFromUrl: () => ({ filterMode: "all", sortNewestFirst: true }),
  updateDailyDashboardUrlWithState: () => {},
}));

vi.mock("../../static/dashboard-utils.js", () => ({
  filterMessages: (messages) => messages,
  sortMessages: (messages) => messages,
  getFilterHeading: () => "Messages (0)",
}));

vi.mock("../../static/companies-service.js", () => {
  const researchSpy = vi.fn(async () => ({
    task_id: "t1",
    status: "pending",
  }));
  class CompaniesService {
    async getMessages() {
      return [];
    }
    research = researchSpy;
    async generateReply() {
      return {};
    }
    async saveReply() {
      return {};
    }
    async archiveMessage() {
      return {};
    }
    async sendAndArchive() {
      return {};
    }
  }
  return { CompaniesService, researchSpy };
});

describe("Daily Dashboard override flags", () => {
  let captured;
  let researchSpy;

  beforeEach(async () => {
    // Ensure global fetch exists
    if (!global.fetch) {
      global.fetch = vi.fn();
    } else {
      global.fetch.mockReset?.();
    }

    captured = captureAlpineFactories();

    // Import the mocked spy to assert calls
    const mod = await import("../../static/companies-service.js");
    researchSpy = mod.researchSpy;

    await import("../../static/daily-dashboard.js");
    document.dispatchEvent(new Event("alpine:init"));
  });

  it("dailyDashboard.research passes override flags to CompaniesService.research", async () => {
    expect(typeof captured.dailyDashboard).toBe("function");
    const component = captured.dailyDashboard();
    await component.init?.();

    const message = {
      company_id: "co-1",
      company_name: "Acme",
      _forceLevels: true,
      _forceContacts: false,
    };

    await component.research(message);

    expect(researchSpy).toHaveBeenCalledTimes(1);
    expect(researchSpy).toHaveBeenCalledWith("co-1", {
      force_levels: true,
      force_contacts: false,
    });
  });

  it("defaults override flags to false when not set", async () => {
    const component = captured.dailyDashboard();
    await component.init?.();

    const message = {
      company_id: "co-2",
      company_name: "Beta",
    };

    await component.research(message);

    expect(researchSpy).toHaveBeenCalledWith("co-2", {
      force_levels: false,
      force_contacts: false,
    });
  });

  it("index.html contains override checkboxes markup for messages", () => {
    const html = loadIndexHtml();
    expect(html.includes('aria-label="dd-force-salary"')).toBe(true);
    expect(html.includes('aria-label="dd-force-contacts"')).toBe(true);
  });
});
