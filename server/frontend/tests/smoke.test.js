import { describe, expect, it } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Smoke: index.html loads key sections", () => {
  it("renders both main views containers and essential scripts are referenced", () => {
    setupDocumentWithIndexHtml(document);

    const companyView = document.getElementById("company-management-view");
    const dashboardView = document.getElementById("daily-dashboard-view");
    expect(companyView).toBeTruthy();
    expect(dashboardView).toBeTruthy();

    const scripts = Array.from(
      document.querySelectorAll('script[type="module"]'),
    ).map((s) => s.getAttribute("src") || "");

    // Ensure our core modules are referenced by HTML
    expect(scripts.some((s) => s.includes("/static/app.js"))).toBe(true);
    expect(scripts.some((s) => s.includes("/static/daily-dashboard.js"))).toBe(
      true,
    );
  });
});
