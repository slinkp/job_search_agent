import { describe, expect, it } from "vitest";
import { formatResearchErrors } from "../../static/company-utils.js";

describe("company-utils: formatResearchErrors", () => {
  it("returns empty string for missing input", () => {
    expect(formatResearchErrors(null)).toBe("");
    expect(formatResearchErrors({})).toBe("");
  });

  it("passes through strings", () => {
    const company = { research_errors: "plain error" };
    expect(formatResearchErrors(company)).toBe("plain error");
  });

  it("formats array of strings and objects", () => {
    const company = {
      research_errors: [
        "simple",
        { step: "fetch", error: "timeout" },
        { unexpected: true },
      ],
    };
    const out = formatResearchErrors(company);
    expect(out).toContain("simple");
    expect(out).toContain("fetch: timeout");
    expect(out).toContain("unexpected");
  });

  it("stringifies unknown types", () => {
    const company = { research_errors: { nested: { a: 1 } } };
    const out = formatResearchErrors(company);
    expect(out).toContain("nested");
  });
});
