import { describe, expect, it } from "vitest";
import {
  buildHashForCompany,
  parseViewFromUrl,
  setIncludeAllParam,
} from "../../static/url-utils.js";

describe("url-utils: parseViewFromUrl", () => {
  it("returns daily_dashboard when view=daily", () => {
    expect(parseViewFromUrl("?view=daily")).toBe("daily_dashboard");
  });

  it("returns company_management otherwise", () => {
    expect(parseViewFromUrl("?view=companies")).toBe("company_management");
    expect(parseViewFromUrl("")).toBe("company_management");
    expect(parseViewFromUrl(undefined)).toBe("company_management");
  });

  it("sets include_all param correctly", () => {
    const url = new URL("https://example.com/");
    setIncludeAllParam(url, true);
    expect(url.searchParams.get("include_all")).toBe("true");
    setIncludeAllParam(url, false);
    expect(url.searchParams.has("include_all")).toBe(false);
  });

  it("builds company hash using encodeURIComponent", () => {
    expect(buildHashForCompany("ACME & Sons")).toBe(
      encodeURIComponent("ACME & Sons")
    );
  });
});
