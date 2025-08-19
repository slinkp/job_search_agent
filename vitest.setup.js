import { afterEach } from "vitest";

// Centralize fetch mocking for all tests; suites can override per-need
if (!global.fetch) {
  // eslint-disable-next-line no-undef
  global.fetch = vi.fn();
}

// Ensure DOM starts empty for each test file and isolate mutations
afterEach(() => {
  if (global.document && global.document.body) {
    global.document.body.innerHTML = "";
  }
  // Restore any spies/stubs between tests
  // eslint-disable-next-line no-undef
  vi.restoreAllMocks();
});
