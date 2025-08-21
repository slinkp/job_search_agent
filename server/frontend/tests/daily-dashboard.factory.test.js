import { describe, it, expect, vi, beforeEach } from "vitest";
import { captureAlpineFactories } from "./test-utils.js";

describe("dailyDashboard factory-capture", () => {
  let captured;

  beforeEach(() => {
    captured = captureAlpineFactories();
    // Ensure global fetch exists
    if (!global.fetch) {
      global.fetch = vi.fn();
    }
  });

  it("registers factory and instantiates component", async () => {
    const mod = await import("../../static/daily-dashboard.js");
    expect(mod).toBeTruthy();
    document.dispatchEvent(new Event("alpine:init"));
    expect(Alpine.data).toHaveBeenCalled();
    expect(typeof captured.dailyDashboard).toBe("function");

    // Mock services used inside the component
    vi.mock("../../static/task-polling.js", () => ({
      TaskPollingService: class {
        addResearching() {}
        removeResearching() {}
        addGeneratingMessage() {}
        removeGeneratingMessage() {}
        addSendingMessage() {}
        removeSendingMessage() {}
        pollResearchStatus = vi.fn(async () => ({}));
        pollMessageStatus = vi.fn(async () => ({}));
        pollSendAndArchiveStatus = vi.fn(async () => ({ status: "completed" }));
        getResearchStatusText() { return ""; }
        getResearchStatusClass() { return {}; }
      },
    }));

    vi.mock("../../static/email-scanning.js", () => ({
      EmailScanningService: class {
        scanningEmails = false;
        emailScanStatus = null;
        async scanRecruiterEmails() { return {}; }
        async pollEmailScanStatus() { return { status: "completed" }; }
        getEmailScanStatusText() { return ""; }
        getEmailScanStatusClass() { return ""; }
      },
    }));

    vi.mock("../../static/companies-service.js", () => ({
      CompaniesService: class {
        async getMessages() { return []; }
        async generateReply() { return { task_id: "t1", status: "pending" }; }
        async sendAndArchive() { return { task_id: "t2", status: "pending" }; }
        async research() { return { task_id: "t3", status: "pending" }; }
        async archiveMessage() { return {}; }
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

    // Instantiate component and exercise a few methods
    const instance = captured.dailyDashboard();
    expect(instance).toBeTruthy();

    // Basic state methods should not throw
    expect(instance.filterMode).toBe("all");
    instance.toggleSortOrder();
    expect(typeof instance.getSortButtonText()).toBe("string");

    // No messages case
    await instance.loadMessages();
    expect(Array.isArray(instance.unprocessedMessages)).toBe(true);
  });
});


