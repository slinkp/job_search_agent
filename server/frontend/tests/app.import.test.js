import { describe, expect, it, vi } from "vitest";

describe("app.js import smoke", () => {
  it("imports without throwing and injects style", async () => {
    // Minimal Alpine stub so listeners can bind safely
    global.Alpine = {
      data: vi.fn(),
      start: vi.fn(),
      store: vi.fn(() => ({})),
    };

    // Global fetch stub to avoid accidental network during module evaluation
    // Suites may override as needed
    if (!global.fetch) {
      global.fetch = vi.fn();
    }

    // Import the module under test
    const mod = await import("../../static/app.js");
    expect(mod).toBeTruthy();

    // app.js adds a <style> block to the document head at import-time
    const styleEl = document.head.querySelector("style");
    expect(styleEl).toBeTruthy();

    // Trigger Alpine registration and confirm factory was registered
    document.dispatchEvent(new Event("alpine:init"));
    expect(Alpine.data).toHaveBeenCalled();
  });
});


