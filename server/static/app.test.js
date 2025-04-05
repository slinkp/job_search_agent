import { describe, expect, it } from "vitest";

describe("Basic DOM Test", () => {
  it("can manipulate the DOM", () => {
    // Create a test element
    const div = document.createElement("div");
    div.textContent = "Test Content";
    document.body.appendChild(div);

    // Test DOM manipulation
    expect(document.body.innerHTML).toContain("Test Content");
  });
});
