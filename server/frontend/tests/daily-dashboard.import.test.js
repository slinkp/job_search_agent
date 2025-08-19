import { describe, expect, it, vi } from "vitest";

describe("daily-dashboard.js import smoke", () => {
  it("imports and registers Alpine component without error", async () => {
    global.Alpine = {
      data: vi.fn(),
      start: vi.fn(),
      store: vi.fn(() => ({})),
    };

    if (!global.fetch) {
      global.fetch = vi.fn();
    }

    const mod = await import("../../static/daily-dashboard.js");
    expect(mod).toBeTruthy();
    // daily-dashboard.js registers on 'alpine:init'; trigger it to drive registration
    document.dispatchEvent(new Event("alpine:init"));
    expect(Alpine.data).toHaveBeenCalled();
  });
});


