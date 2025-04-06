import { beforeEach, describe, expect, it } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils";

describe("App", () => {
  beforeEach(() => {
    // Set up document with actual HTML
    setupDocumentWithIndexHtml(document);
  });

  it("can manipulate the DOM", () => {
    // Create a test element
    const div = document.createElement("div");
    div.textContent = "Test Content";
    document.body.appendChild(div);

    // Test that the element is in the document
    expect(document.body.textContent).toContain("Test Content");
  });
});
