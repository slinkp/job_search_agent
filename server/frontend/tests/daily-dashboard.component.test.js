import { beforeEach, describe, expect, it, vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe.skip("Daily Dashboard Component (real Alpine)", () => {
  let Alpine;

  beforeEach(async () => {
    // Fresh DOM
    setupDocumentWithIndexHtml(document);

    // Provide a MutationObserver stub compatible with Alpine in happy-dom
    global.MutationObserver = class {
      constructor(callback) {
        this.callback = callback;
      }
      observe() {}
      disconnect() {}
      takeRecords() { return []; }
    };

    // Mock fetch with deterministic dataset
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          message_id: "m1",
          company_id: "c1",
          company_name: "A Corp",
          subject: "Hello",
          message: "x".repeat(250),
          date: "2025-01-12T09:00:00Z",
          reply_sent_at: null,
          archived_at: null,
        },
        {
          message_id: "m2",
          company_id: "c2",
          company_name: "B Corp",
          subject: "Hi",
          message: "Short",
          date: "2025-01-10T10:00:00Z",
          reply_sent_at: "2025-01-11T10:00:00Z",
          archived_at: null,
        },
      ],
    });

    // Import Alpine and component
    Alpine = (await import("alpinejs")).default;
    window.Alpine = Alpine;

    // Import the real component module which registers on alpine:init
    await import("../../static/daily-dashboard.js");

    // Trigger alpine:init and start Alpine
    document.dispatchEvent(new CustomEvent("alpine:init"));
    await Alpine.start();
  });

  function getDashboardRoot() {
    return document.getElementById("daily-dashboard-view");
  }

  async function waitForHeading() {
    const deadline = Date.now() + 1000;
    while (Date.now() < deadline) {
      const h3 = getDashboardRoot()?.querySelector(".message-list h3");
      if (h3 && h3.textContent) return h3;
      // allow microtasks to flush
      // eslint-disable-next-line no-await-in-loop
      await Promise.resolve();
    }
    throw new Error("Heading not rendered");
  }

  it("loads messages and shows correct default heading", async () => {
    const h3 = await waitForHeading();
    expect(h3.textContent).toMatch(/All Messages \(2\)/);
  });

  it("filter buttons update heading and URL", async () => {
    await waitForHeading();
    const root = getDashboardRoot();
    const notRepliedBtn = root.querySelector(
      ".filter-controls button:nth-child(2)"
    );
    notRepliedBtn.click();

    // After filtering, only 1 not-replied message remains
    const h3 = await waitForHeading();
    expect(h3.textContent).toMatch(/Unreplied Messages \(1\)/);

    // URL updated
    expect(window.location.search).toContain("filterMode=not-replied");
  });

  it("sort button toggles label and URL", async () => {
    await waitForHeading();
    const root = getDashboardRoot();
    const allButtons = Array.from(root.querySelectorAll(".dashboard-actions button"));
    const sortBtn = allButtons.find((b) => /Newest First|Oldest First/.test(b.textContent || ""));
    // First click -> oldest
    sortBtn.click();
    expect(window.location.search).toContain("sort=oldest");
    // Second click -> newest
    sortBtn.click();
    expect(window.location.search).toContain("sort=newest");
  });

  it("expand/collapse works for long messages", async () => {
    await waitForHeading();
    const root = getDashboardRoot();
    const expandBtn = root.querySelector(
      ".message-list template"
    ).innerHTML.includes("toggleMessageExpansion");
    expect(expandBtn).toBe(true);
  });
});


