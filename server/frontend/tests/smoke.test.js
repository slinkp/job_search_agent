import { describe, expect, it, vi } from "vitest";
import { loadIndexHtml, setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Smoke: index.html loads key sections", () => {
  it("renders both main views containers and essential scripts are referenced", () => {
    setupDocumentWithIndexHtml(document);

    const companyView = document.getElementById("company-management-view");
    const dashboardView = document.getElementById("daily-dashboard-view");
    expect(companyView).toBeTruthy();
    expect(dashboardView).toBeTruthy();

    // Inspect raw HTML to assert referenced scripts without triggering fetches
    const rawHtml = loadIndexHtml();
    expect(rawHtml.includes('/static/app.js')).toBe(true);
    expect(rawHtml.includes('/static/daily-dashboard.js')).toBe(true);
  });

  it("imports app.js and daily-dashboard.js without errors and registers Alpine factories", async () => {
    setupDocumentWithIndexHtml(document);
    global.Alpine = {
      data: vi.fn(),
      start: vi.fn(),
      store: vi.fn(() => ({})),
    };
    if (!global.fetch) global.fetch = vi.fn();

    const appMod = await import("../../static/app.js");
    expect(appMod).toBeTruthy();
    const ddMod = await import("../../static/daily-dashboard.js");
    expect(ddMod).toBeTruthy();

    document.dispatchEvent(new Event("alpine:init"));
    expect(Alpine.data).toHaveBeenCalled();
  });
});
