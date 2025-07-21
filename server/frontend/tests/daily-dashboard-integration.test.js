import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Daily Dashboard Integration", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    // Reset document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Spy on console.error to catch JavaScript errors
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should have required DOM elements for daily dashboard", () => {
    // Verify the dashboard container exists in HTML
    const dashboardView = document.getElementById("daily-dashboard-view");
    expect(dashboardView).toBeTruthy();

    // Verify dashboard header exists
    const dashboardHeader = dashboardView.querySelector(".dashboard-header");
    expect(dashboardHeader).toBeTruthy();

    // Verify dashboard title exists
    const dashboardTitle = dashboardHeader.querySelector("h2");
    expect(dashboardTitle).toBeTruthy();
    expect(dashboardTitle.textContent).toBe("Daily Dashboard");

    // Verify dashboard actions container exists
    const dashboardActions =
      dashboardHeader.querySelector(".dashboard-actions");
    expect(dashboardActions).toBeTruthy();

    // Verify all three buttons exist
    const buttons = dashboardActions.querySelectorAll("button");
    expect(buttons.length).toBe(3);
    expect(buttons[0].textContent.trim()).toBe("Scan Emails");
    expect(buttons[1].textContent.trim()).toBe("Refresh");

    // Verify sort button exists and has Alpine directive
    const sortButton = buttons[2];
    expect(sortButton).toBeTruthy();
    expect(sortButton.querySelector("span")).toBeTruthy();
    expect(sortButton.querySelector("span").hasAttribute("x-text")).toBe(true);
    expect(sortButton.querySelector("span").getAttribute("x-text")).toBe(
      "getSortButtonText()"
    );
  });

  it("should have proper Alpine data binding structure", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");

    // Verify Alpine data is bound (x-data attribute exists)
    expect(dashboardView.hasAttribute("x-data")).toBe(true);
    expect(dashboardView.getAttribute("x-data")).toBe("dailyDashboard");

    // Verify Alpine init is bound
    expect(dashboardView.hasAttribute("x-init")).toBe(true);
    expect(dashboardView.getAttribute("x-init")).toBe("init()");
  });

  it("should have view mode toggle buttons", () => {
    // Verify toggle buttons exist
    const toggleButtons = document.querySelectorAll(".view-mode-toggle button");
    expect(toggleButtons.length).toBe(2);

    // Verify button text
    expect(toggleButtons[0].textContent.trim()).toBe("Company Management");
    expect(toggleButtons[1].textContent.trim()).toBe("Daily Dashboard");
  });

  it("should have both view containers", () => {
    // Get both view containers
    const companyView = document.getElementById("company-management-view");
    const dashboardView = document.getElementById("daily-dashboard-view");

    expect(companyView).toBeTruthy();
    expect(dashboardView).toBeTruthy();
  });

  it("should have proper CSS classes for styling", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");

    // Verify CSS classes exist for styling
    expect(dashboardView.querySelector(".loading-message")).toBeTruthy();
    expect(dashboardView.querySelector(".no-messages")).toBeTruthy();
    expect(dashboardView.querySelector(".message-list")).toBeTruthy();
  });

  it("should have message item structure when data is present", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      // Verify message item template structure
      const template = messageList.querySelector("template");
      expect(template).toBeTruthy();
      expect(template.hasAttribute("x-for")).toBe(true);

      // Verify the template has content (Alpine will render this when data is present)
      expect(template.innerHTML).toContain("message-item");
      expect(template.innerHTML).toContain("message-info");
      expect(template.innerHTML).toContain("message-actions");
    }
  });

  it("should have sorting functionality implemented", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");

    // Verify sort button exists and has click handler
    const sortButton = dashboardView.querySelector(
      ".dashboard-actions button:last-child"
    );
    expect(sortButton).toBeTruthy();
    expect(sortButton.hasAttribute("@click")).toBe(true);
    expect(sortButton.getAttribute("@click")).toBe("toggleSortOrder()");

    // Verify the template uses sortedMessages instead of unprocessedMessages
    const messageList = dashboardView.querySelector(".message-list");
    if (messageList) {
      const template = messageList.querySelector("template");
      expect(template.hasAttribute("x-for")).toBe(true);
      expect(template.getAttribute("x-for")).toBe("company in sortedMessages");
    }
  });

  it("should have expandable message functionality", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");

      // Verify message preview uses the new getMessagePreview function
      expect(template.innerHTML).toContain("getMessagePreview(company)");

      // Verify expand button exists with proper attributes
      expect(template.innerHTML).toContain("expand-button");
      expect(template.innerHTML).toContain("toggleMessageExpansion");
      expect(template.innerHTML).toContain("getExpandButtonText");

      // Verify expand button only shows for long messages
      expect(template.innerHTML).toContain(
        'x-show="company.recruiter_message?.message?.length > 200"'
      );
    }
  });

  it("should have proper message preview structure", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");

      // Verify message preview container exists
      expect(template.innerHTML).toContain("message-preview");

      // Verify message preview has paragraph for text
      expect(template.innerHTML).toContain(
        '<p x-text="getMessagePreview(company)"></p>'
      );

      // Verify expand button is properly structured
      expect(template.innerHTML).toContain('class="expand-button outline"');
    }
  });
});
