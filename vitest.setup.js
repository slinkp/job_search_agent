import { Window } from "happy-dom";
import { afterAll, afterEach, beforeAll } from "vitest";
import { setupDocumentWithIndexHtml } from "./server/frontend/tests/test-utils.js";

// Set up global window object
const window = new Window();
global.window = window;
global.document = window.document;
global.navigator = window.navigator;
global.HTMLElement = window.HTMLElement;

// Set up document before each test
beforeAll(() => {
  setupDocumentWithIndexHtml(document);
});

// Clean up after each test
afterEach(() => {
  document.body.innerHTML = "";
});

// Clean up after all tests
afterAll(() => {
  delete global.window;
  delete global.document;
  delete global.navigator;
  delete global.HTMLElement;
});
