import { Window } from "happy-dom";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

// Set up global window object
beforeAll(() => {
  // Create a new window for each test suite
  const window = new Window();
  global.window = window;
  global.document = window.document;
  global.navigator = window.navigator;

  // Mock fetch if not already mocked
  if (!global.fetch) {
    global.fetch = vi.fn();
  }
});

// Clean up after each test
afterEach(() => {
  // Reset the document body
  document.body.innerHTML = "";

  // Reset all mocks
  vi.resetAllMocks();
});

// Clean up after all tests
afterAll(() => {
  // Clean up global objects
  delete global.window;
  delete global.document;
  delete global.navigator;
});
