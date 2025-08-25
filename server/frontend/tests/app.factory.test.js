import { beforeEach, describe, expect, it, vi } from "vitest";
import { captureAlpineFactories, loadIndexHtml } from "./test-utils.js";

describe("app/companyList factory-capture", () => {
  let captured;

  beforeEach(() => {
    captured = captureAlpineFactories();
    // Ensure global fetch exists
    if (!global.fetch) {
      global.fetch = vi.fn();
    }
    // Align document origin with URLs used by mocked url-utils
    Object.defineProperty(window, "location", {
      value: {
        href: "http://localhost:3000/",
        origin: "http://localhost:3000",
        search: "",
        hash: "",
        pathname: "/",
      },
      writable: true,
    });
    // Stub history to avoid cross-origin enforcement in happy-dom
    Object.defineProperty(window, "history", {
      value: {
        replaceState: vi.fn(),
        pushState: vi.fn(),
      },
      writable: true,
    });
  });

  it("registers companyList factory and basic methods work", async () => {
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
        getResearchStatusText() {
          return "";
        }
        getResearchStatusClass() {
          return {};
        }
        getMessageStatusText() {
          return "";
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

    vi.mock("../../static/company-research.js", () => ({
      CompanyResearchService: class {},
    }));

    vi.mock("../../static/companies-service.js", () => ({
      CompaniesService: class {
        async getCompanies() {
          return [];
        }
        async getCompany(id) {
          return { company_id: id, name: "Test Co" };
        }
        async loadCompany(id) {
          return { company_id: id, name: "Test Co" };
        }
        async loadMessageAndCompany(messageId) {
          return {
            company: { company_id: "c1", name: "Test Co" },
            message: { message_id: messageId },
          };
        }
        async saveReply() {
          return { reply_message: "Saved" };
        }
        async sendAndArchive() {
          return { task_id: "t1", status: "pending" };
        }
        async archiveMessage() {
          return {};
        }
        async generateReply() {
          return { task_id: "t2", status: "pending" };
        }
        async research() {
          return { task_id: "t3", status: "pending" };
        }
        async importCompanies() {
          return { task_id: "imp1" };
        }
        async pollTask() {
          return { status: "completed" };
        }
        async updateCompanyDetails() {
          return {};
        }
        async getMessages() {
          return [];
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
      formatRecruiterMessageDate: (d) => String(d || ""),
      isUrl: (v) => typeof v === "string" && /^https?:\/\//.test(v),
      modalUtils: {
        showModal: () => {},
        closeModal: () => {},
        modalIds: {
          EDIT: "editModal",
          RESEARCH_COMPANY: "research-company-modal",
          IMPORT_COMPANIES: "import-companies-modal",
        },
      },
    }));

    vi.mock("../../static/url-utils.js", () => ({
      setIncludeAllParam: (url, includeAll) => {
        if (includeAll) url.searchParams.set("include_all", "true");
        else url.searchParams.delete("include_all");
      },
      buildHashForCompany: (id) => `#${id}`,
      parseViewFromUrl: () => "company_management",
      urlUtils: {
        createUrl() {
          return new URL(window.location.href || "http://localhost:3000/");
        },
        updateUrlParams(params) {
          const u = new URL(window.location.href || "http://localhost:3000/");
          for (const [k, v] of Object.entries(params)) {
            if (v == null) u.searchParams.delete(k);
            else u.searchParams.set(k, v);
          }
          window.history.replaceState({}, "", u);
          return u;
        },
        removeUrlParams(keys) {
          const u = new URL(window.location.href || "http://localhost:3000/");
          keys.forEach((k) => u.searchParams.delete(k));
          window.history.replaceState({}, "", u);
          return u;
        },
        setHash(hash) {
          const u = new URL(window.location.href || "http://localhost:3000/");
          u.hash = hash;
          window.history.replaceState({}, "", u);
          return u;
        },
      },
    }));

    const mod = await import("../../static/app.js");
    expect(mod).toBeTruthy();
    document.dispatchEvent(new Event("alpine:init"));
    expect(Alpine.data).toHaveBeenCalled();

    expect(typeof captured.companyList).toBe("function");
    const instance = captured.companyList();
    expect(instance).toBeTruthy();

    // Exercise a few methods to execute code paths
    await instance.refreshAllCompanies(false);
    expect(Array.isArray(instance.companies)).toBe(true);

    instance.toggleSort("name");
    expect(instance.sortField).toBe("name");
    const sorted = instance.sortedAndFilteredCompanies;
    expect(Array.isArray(sorted)).toBe(true);

    // Toggle view mode and ensure URL update is invoked without throwing
    instance.toggleViewMode();
    expect(["company_management", "daily_dashboard"]).toContain(
      instance.viewMode
    );
  });

  it("should have HTML structure for displaying company aliases", () => {
    // Load the raw HTML content
    const rawHtml = loadIndexHtml();

    // Check that the aliases section exists in the HTML content
    expect(rawHtml).toContain('class="company-aliases-details"');
    expect(rawHtml).toContain(
      'x-show="company.aliases && company.aliases.length > 0"'
    );
    expect(rawHtml).toContain("<strong>Aliases:</strong>");
    expect(rawHtml).toContain('x-for="alias in company.aliases"');
    expect(rawHtml).toContain('x-text="alias.alias"');
    expect(rawHtml).toContain("x-text=\"' (' + alias.source + ')'\"");
    expect(rawHtml).toContain('x-if="!alias.is_active"');
    expect(rawHtml).toContain("(Inactive)");
  });

  it("should have HTML structure for add alias form", () => {
    // Load the raw HTML content
    const rawHtml = loadIndexHtml();

    // Check that the add alias form exists in the HTML content
    expect(rawHtml).toContain('class="add-alias-form"');
    expect(rawHtml).toContain("<strong>Add Alias:</strong>");
    expect(rawHtml).toContain('x-model="newAlias"');
    expect(rawHtml).toContain('placeholder="Enter company alias"');
    expect(rawHtml).toContain('x-model="setAsCanonical"');
    expect(rawHtml).toContain("checked");
    expect(rawHtml).toContain("Set as canonical name");
    expect(rawHtml).toContain('@submit.prevent="addAlias(company.company_id)"');
  });
});
