import { describe, expect, it } from "vitest";
import { computeMessagePreview } from "../../static/message-utils.js";

describe("computeMessagePreview", () => {
  it("should return full message when expanded", () => {
    const message = {
      message:
        "This is a long message that should be shown in full when expanded",
    };
    const result = computeMessagePreview(message, true);
    expect(result).toBe(
      "This is a long message that should be shown in full when expanded"
    );
  });

  it("should return truncated message when not expanded and message is longer than limit", () => {
    const message = {
      message:
        "This is a very long message that should be truncated when not expanded. It has more than 200 characters to ensure it gets cut off properly and shows the ellipsis at the end of the truncated text.",
    };
    const result = computeMessagePreview(message, false);
    expect(result).toBe(
      "This is a very long message that should be truncated when not expanded. It has more than 200 characters to ensure it gets cut off properly and shows the ellipsis at the end of the truncated text."
    );
  });

  it("should return original message when not expanded and message is shorter than limit", () => {
    const message = { message: "Short message" };
    const result = computeMessagePreview(message, false);
    expect(result).toBe("Short message");
  });

  it("should return 'No message content' when message is null", () => {
    const message = { message: null };
    const result = computeMessagePreview(message, false);
    expect(result).toBe("No message content");
  });

  it("should return 'No message content' when message is undefined", () => {
    const message = { message: undefined };
    const result = computeMessagePreview(message, false);
    expect(result).toBe("No message content");
  });

  it("should return 'No message content' when message property is missing", () => {
    const message = {};
    const result = computeMessagePreview(message, false);
    expect(result).toBe("No message content");
  });

  it("should respect custom limit parameter", () => {
    const message = {
      message:
        "This message is exactly 50 characters long and should be truncated",
    };
    const result = computeMessagePreview(message, false, 30);
    expect(result).toBe("This message is exactly 50 cha...");
  });

  it("should return full message when expanded even with custom limit", () => {
    const message = {
      message:
        "This message is exactly 50 characters long and should be truncated",
    };
    const result = computeMessagePreview(message, true, 30);
    expect(result).toBe(
      "This message is exactly 50 characters long and should be truncated"
    );
  });
});
