import { describe, expect, it } from "vitest";
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
});
