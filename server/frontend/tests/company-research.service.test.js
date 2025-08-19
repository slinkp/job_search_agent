import { describe, expect, it, vi, beforeEach } from "vitest";

// Important: do NOT mock the module here; we want real coverage
import { CompanyResearchService } from "../../static/company-research.js";

describe("CompanyResearchService (real) smoke", () => {
  beforeEach(() => {
    // Fresh fetch stub for each test
    global.fetch = vi.fn();
  });

  it("submitResearch validates input and calls fetch", async () => {
    const svc = new CompanyResearchService();

    await expect(svc.submitResearch({ url: "", name: "" })).rejects.toThrow(
      /either a company URL or name/i
    );

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ task_id: "t1" }),
    });

    const res = await svc.submitResearch({ url: "https://x.com" });
    expect(res).toEqual({ task_id: "t1" });
    expect(fetch).toHaveBeenCalled();
  });

  it("pollResearchTask fetches task json", async () => {
    const svc = new CompanyResearchService();

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: "completed" }),
    });

    const res = await svc.pollResearchTask("task-123");
    expect(res).toEqual({ status: "completed" });
  });
});


