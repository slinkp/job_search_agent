import { beforeEach, describe, expect, it, vi } from "vitest";
import { captureAlpineFactories } from "./test-utils.js";

// Mock dependencies BEFORE importing the component module
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
    async pollMessageStatus() {
      return { status: "completed" };
    }
    async pollSendAndArchiveStatus() {
      return { status: "completed" };
    }
    getResearchStatusText() {
      return "";
    }
    getResearchStatusClass() {
      return {};
    }
  },
}));

vi.mock("../../static/email-scanning.js", () => ({
  EmailScanningService: class {
    scanningEmails = false;
    emailScanStatus = null;
    async scanRecruiterEmails() {
      return {};
    }
    async pollEmailScanStatus() {
      return { status: "completed" };
    }
    getEmailScanStatusText() {
      return "";
    }
    getEmailScanStatusClass() {
      return "";
    }
  },
}));

vi.mock("../../static/companies-service.js", () => ({
  CompaniesService: class {
    async getMessages() {
      return [];
    }
    async generateReply() {
      return { task_id: "t1", status: "pending" };
    }
    async sendAndArchive() {
      return { task_id: "t2", status: "pending" };
    }
    async research() {
      return { task_id: "t3", status: "pending" };
    }
    async archiveMessage() {
      return {};
    }
  },
}));

vi.mock("../../static/ui-utils.js", () => ({
  confirmDialogs: {
    archiveWithoutReply: () => true,
    sendAndArchive: () => true,
    archiveScope: () => "all",
  },
  errorLogger: { logFailedTo: () => {}, logError: () => {} },
  showError: () => {},
  showSuccess: () => {},
  formatMessageDate: (d) => String(d || ""),
}));

describe("dailyDashboard factory-capture flows", () => {
  let captured;

  beforeEach(() => {
    captured = captureAlpineFactories();
    if (!global.fetch) global.fetch = vi.fn();
  });

  it("executes core flows on real component instance", async () => {
    const mod = await import("../../static/daily-dashboard.js");
    expect(mod).toBeTruthy();
    document.dispatchEvent(new Event("alpine:init"));
    expect(typeof captured.dailyDashboard).toBe("function");

    const instance = captured.dailyDashboard();
    expect(instance).toBeTruthy();

    // Exercise URL/state methods
    instance.setFilterMode("replied");
    expect(instance.filterMode).toBe("replied");
    instance.toggleSortOrder();
    expect(typeof instance.getSortButtonText()).toBe("string");

    // Prepare a message object
    const message = {
      message_id: "m1",
      company_id: "c1",
      company_name: "Co",
      message: "Hello",
      reply_message: "Draft",
    };

    // Exercise actions
    await instance.generateReply(message);
    await instance.sendAndArchive({ ...message, reply_message: "Send me" });
    await instance.research({ ...message });
    await instance.archive("m1");

    // Basic state accessors
    expect(instance.isGeneratingMessage(message)).toBe(false);
    expect(instance.isSendingMessage(message)).toBe(false);
  });
});
