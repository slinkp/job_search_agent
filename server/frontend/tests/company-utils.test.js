import { describe, expect, it } from "vitest";
import {
  filterCompanies,
  formatResearchErrors,
  normalizeCompanies,
  normalizeCompany,
  normalizeCompanyNameForComparison,
  sortCompanies,
} from "../../static/company-utils.js";

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

describe("company-utils: filterCompanies & sortCompanies", () => {
  const companies = [
    {
      name: "B",
      updated_at: "2025-01-02T00:00:00Z",
      sent_at: null,
      research_completed_at: null,
    },
    {
      name: "A",
      updated_at: "2025-01-03T00:00:00Z",
      sent_at: "2025-01-10",
      research_completed_at: "2025-01-11",
    },
    {
      name: "C",
      updated_at: "2025-01-01T00:00:00Z",
      sent_at: null,
      research_completed_at: "2025-01-05",
    },
  ];

  it("filters by reply-sent / reply-not-sent / researched / not-researched", () => {
    expect(filterCompanies(companies, "reply-sent").map((c) => c.name)).toEqual(
      ["A"]
    );
    expect(
      filterCompanies(companies, "reply-not-sent").map((c) => c.name)
    ).toEqual(["B", "C"]);
    expect(filterCompanies(companies, "researched").map((c) => c.name)).toEqual(
      ["A", "C"]
    );
    expect(
      filterCompanies(companies, "not-researched").map((c) => c.name)
    ).toEqual(["B"]);
    expect(filterCompanies(companies, "all").length).toBe(3);
  });

  it("sorts by updated_at (date) and name", () => {
    const byUpdatedAsc = sortCompanies(companies, "updated_at", true).map(
      (c) => c.name
    );
    expect(byUpdatedAsc).toEqual(["C", "B", "A"]);

    const byUpdatedDesc = sortCompanies(companies, "updated_at", false).map(
      (c) => c.name
    );
    expect(byUpdatedDesc).toEqual(["A", "B", "C"]);

    const byNameAsc = sortCompanies(companies, "name", true).map((c) => c.name);
    expect(byNameAsc).toEqual(["A", "B", "C"]);

    const byNameDesc = sortCompanies(companies, "name", false).map(
      (c) => c.name
    );
    expect(byNameDesc).toEqual(["C", "B", "A"]);
  });

  it("sorts by activity_at when requested", () => {
    const withActivity = [
      { name: "A", activity_at: "2025-01-05T12:00:00Z" },
      { name: "B", activity_at: "2025-01-03T12:00:00Z" },
      { name: "C", activity_at: null },
    ];

    const asc = sortCompanies(withActivity, "activity_at", true).map(
      (c) => c.name
    );
    expect(asc).toEqual(["C", "B", "A"]);

    const desc = sortCompanies(withActivity, "activity_at", false).map(
      (c) => c.name
    );
    expect(desc).toEqual(["A", "B", "C"]);
  });

  it("normalizes details field on company/companies", () => {
    const c = normalizeCompany({ name: "Z" });
    expect(c.details).toEqual({});
    const list = normalizeCompanies([
      { name: "Z" },
      { name: "Y", details: { a: 1 } },
    ]);
    expect(list[0].details).toEqual({});
    expect(list[1].details).toEqual({ a: 1 });
  });
});

describe("company-utils: normalizeCompanyNameForComparison", () => {
  it("handles nullish and basic strings", () => {
    expect(normalizeCompanyNameForComparison(null)).toBe("");
    expect(normalizeCompanyNameForComparison(undefined)).toBe("");
    expect(normalizeCompanyNameForComparison("  Acme Corp  ")).toBe(
      "acme corp",
    );
  });

  it("normalizes case, ampersand, and whitespace", () => {
    expect(normalizeCompanyNameForComparison("Acme & Co")).toBe("acme and co");
    expect(normalizeCompanyNameForComparison(" acme   and\tco ")).toBe(
      "acme and co",
    );
    expect(
      normalizeCompanyNameForComparison("ACME   CORPORATION"),
    ).toBe("acme corporation");
  });

  it("produces equal strings for equivalent names", () => {
    const a = normalizeCompanyNameForComparison("Acme Corp");
    const b = normalizeCompanyNameForComparison("  acme corp ");
    const c = normalizeCompanyNameForComparison("ACME   CORP");
    expect(a).toBe(b);
    expect(b).toBe(c);
  });
});
