import { Window } from "happy-dom";
import { afterAll, afterEach, beforeAll } from "vitest";

// Set up global window object
beforeAll(() => {
  // Create a new window for each test suite
  const window = new Window();
  global.window = window;
  global.document = window.document;
  global.navigator = window.navigator;

  // Mock Alpine.js
  window.Alpine = {
    start: () => {},
    data: (name, data) => data,
    store: {},
  };
});

// Clean up after each test
afterEach(() => {
  // Reset the document body
  document.body.innerHTML = "";
});

// Clean up after all tests
afterAll(() => {
  // Clean up global objects
  delete global.window;
  delete global.document;
  delete global.navigator;
});
