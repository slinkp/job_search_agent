import { describe, it, expect } from "vitest";
import {
  filterMessages,
  sortMessages,
  parseUrlState,
  buildUpdatedSearch,
  getFilterHeading,
} from "../../static/dashboard-utils.js";

describe("dashboard-utils", () => {
  const messages = [
    {
      message_id: "1",
      date: "2025-01-10T10:00:00Z",
      reply_sent_at: null,
      archived_at: null,
    },
    {
      message_id: "2",
      date: "2025-01-12T09:00:00Z",
      reply_sent_at: "2025-01-12T10:00:00Z",
      archived_at: null,
    },
    {
      message_id: "3",
      date: null,
      reply_sent_at: null,
      archived_at: "2025-01-11T08:00:00Z",
    },
  ];

  it("filters messages by mode", () => {
    expect(filterMessages(messages, "all").length).toBe(3);
    expect(filterMessages(messages, "replied").map((m) => m.message_id)).toEqual([
      "2",
    ]);
    expect(
      filterMessages(messages, "not-replied").map((m) => m.message_id)
    ).toEqual(["1", "3"]);
    expect(filterMessages(messages, "archived").map((m) => m.message_id)).toEqual([
      "3",
    ]);
  });

  it("sorts messages newest first by default and handles null dates", () => {
    const sortedNewest = sortMessages(messages, true).map((m) => m.message_id);
    expect(sortedNewest).toEqual(["2", "1", "3"]);

    const sortedOldest = sortMessages(messages, false).map((m) => m.message_id);
    expect(sortedOldest).toEqual(["1", "2", "3"]);
  });

  it("parses URL state with defaults", () => {
    expect(parseUrlState("")).toEqual({ filterMode: "all", sortNewestFirst: true });
    expect(parseUrlState("filterMode=replied&sort=oldest")).toEqual({
      filterMode: "replied",
      sortNewestFirst: false,
    });
    // invalid filter falls back to all
    expect(parseUrlState("filterMode=invalid&sort=newest")).toEqual({
      filterMode: "all",
      sortNewestFirst: true,
    });
  });

  it("builds updated search preserving other params", () => {
    const search = buildUpdatedSearch("view=daily&tab=2", {
      filterMode: "not-replied",
      sortNewestFirst: false,
    });
    const params = new URLSearchParams(search);
    expect(params.get("view")).toBe("daily");
    expect(params.get("tab")).toBe("2");
    expect(params.get("filterMode")).toBe("not-replied");
    expect(params.get("sort")).toBe("oldest");
  });

  it("returns filter headings", () => {
    expect(getFilterHeading("all", 5)).toBe("All Messages (5)");
    expect(getFilterHeading("not-replied", 2)).toBe("Unreplied Messages (2)");
    expect(getFilterHeading("archived", 1)).toBe("Archived Messages (1)");
    expect(getFilterHeading("replied", 3)).toBe("Replied Messages (3)");
    expect(getFilterHeading("something", 0)).toBe("Messages (0)");
  });
});


