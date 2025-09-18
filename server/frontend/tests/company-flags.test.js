import { describe, it, expect, beforeEach, vi } from "vitest";
import { captureAlpineFactories, loadIndexHtml } from "./test-utils.js";

// Mocks
vi.mock("../../static/task-polling.js", () => ({
  TaskPollingService: class {
    addResearching() {}
    removeResearching() {}
    async pollResearchStatus() {
      return { status: "completed" };
    }
    getResearchStatusText() {
      return "";
    }
    getResearchStatusClass() {
      return "";
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
      DUPLICATE: "duplicate-modal",
    },
  },
}));

vi.mock("../../static/company-research.js", () => ({
  CompanyResearchService: class {},
}));

vi.mock("../../static/email-scanning.js", () => ({
  EmailScanningService: class {
    getEmailScanStatusText() {
      return "";
    }
    getEmailScanStatusClass() {
      return "";
    }
    get scanningEmails() {
      return false;
    }
    get emailScanStatus() {
      return null;
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
  buildHashForCompany: (id) => `#${id}`,
  parseViewFromUrl: () => "company_management",
  setIncludeAllParam: () => {},
  urlUtils: {
    createUrl() {
      return new URL("http://localhost/");
    },
    updateUrlParams() {},
    removeUrlParams() {},
  },
}));

vi.mock("../../static/companies-service.js", () => {
  const researchSpy = vi.fn(async (companyId, options) => ({
    task_id: "t1",
    status: "pending",
  }));
  class CompaniesService {
    async getCompanies() {
      return [];
    }
    async getCompany(id) {
      return { company_id: id, name: "Test Co" };
    }
    async getPotentialDuplicates() {
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
    async importCompanies() {
      return {};
    }
    async submitResearch() {
      return {};
    }
    async pollResearchTask() {
      return {};
    }
    async pollTask() {
      return {};
    }
    async scanEmails() {
      return {};
    }
    async getMessages() {
      return [];
    }
    async addAlias() {
      return {};
    }
    async mergeCompanies() {
      return { task_id: "t1" };
    }
    async makeAliasCanonical() {
      return {};
    }
  }
  return { CompaniesService, researchSpy };
});

describe("Companies view override flags", () => {
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

    await import("../../static/app.js");
    document.dispatchEvent(new Event("alpine:init"));
  });

  it("companyList.research passes override flags to CompaniesService.research", async () => {
    expect(typeof captured.companyList).toBe("function");
    const component = captured.companyList();

    const company = {
      company_id: "co-1",
      name: "Acme",
      _forceLevels: true,
      _forceContacts: false,
    };

    await component.research(company);

    expect(researchSpy).toHaveBeenCalledTimes(1);
    expect(researchSpy).toHaveBeenCalledWith("co-1", {
      force_levels: true,
      force_contacts: false,
    });
  });

  it("defaults override flags to false when not set", async () => {
    const component = captured.companyList();

    const company = {
      company_id: "co-2",
      name: "Beta",
    };

    await component.research(company);

    expect(researchSpy).toHaveBeenCalledWith("co-2", {
      force_levels: false,
      force_contacts: false,
    });
  });

  it("index.html contains override checkboxes markup", () => {
    const html = loadIndexHtml();
    expect(html.includes('aria-label="force-salary"')).toBe(true);
    expect(html.includes('aria-label="force-contacts"')).toBe(true);
  });
});
