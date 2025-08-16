import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils.js";

describe("Daily Dashboard Integration", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up document with actual HTML
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

    // Verify filter controls exist
    const filterControls = dashboardActions.querySelector(".filter-controls");
    expect(filterControls).toBeTruthy();

    // Verify filter buttons exist
    const filterButtons = filterControls.querySelectorAll("button");
    expect(filterButtons.length).toBe(3);
    expect(filterButtons[0].textContent.trim()).toBe("All");
    expect(filterButtons[1].textContent.trim()).toBe("Not Replied");
    expect(filterButtons[2].textContent.trim()).toBe("Archived");

    // Verify other buttons exist (scan emails, refresh, sort)
    const allButtons = dashboardActions.querySelectorAll("button");
    expect(allButtons.length).toBeGreaterThanOrEqual(6); // 3 filter buttons + 3 other buttons

    // Verify that buttons have Alpine directives
    const buttonsWithClick =
      dashboardActions.querySelectorAll("button[@click]");
    expect(buttonsWithClick.length).toBeGreaterThanOrEqual(6);
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

    // Verify filter buttons have click handlers
    const filterButtons = dashboardView.querySelectorAll(
      ".filter-controls button"
    );
    expect(filterButtons.length).toBe(3);
    expect(filterButtons[0].hasAttribute("@click")).toBe(true);
    expect(filterButtons[0].getAttribute("@click")).toBe(
      "setFilterMode('all')"
    );
    expect(filterButtons[1].hasAttribute("@click")).toBe(true);
    expect(filterButtons[1].getAttribute("@click")).toBe(
      "setFilterMode('not-replied')"
    );
    expect(filterButtons[2].hasAttribute("@click")).toBe(true);
    expect(filterButtons[2].getAttribute("@click")).toBe(
      "setFilterMode('archived')"
    );

    // Verify that buttons have Alpine directives
    const buttonsWithClick = dashboardView.querySelectorAll("button[@click]");
    expect(buttonsWithClick.length).toBeGreaterThanOrEqual(6);

    // Verify the template uses sortedMessages instead of unprocessedMessages
    const messageList = dashboardView.querySelector(".message-list");
    if (messageList) {
      const template = messageList.querySelector("template");
      expect(template.hasAttribute("x-for")).toBe(true);
      expect(template.getAttribute("x-for")).toBe("message in sortedMessages");
    }
  });

  it("should have expandable message functionality", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");

      // Verify message preview uses the new getMessagePreview function
      expect(template.innerHTML).toContain("getMessagePreview(message)");

      // Verify expand button exists with proper attributes
      expect(template.innerHTML).toContain("expand-button");
      expect(template.innerHTML).toContain("toggleMessageExpansion");
      expect(template.innerHTML).toContain("getExpandButtonText");

      // Verify expand button only shows for long messages
      expect(template.innerHTML).toContain(
        'x-show="message.message?.length > 200"'
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
        '<p x-text="getMessagePreview(message)"></p>'
      );

      // Verify expand button is properly structured
      expect(template.innerHTML).toContain('class="expand-button outline"');
    }
  });

  it("should have research button properly wired up", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");

      // Verify research section exists
      expect(template.innerHTML).toContain("research-section");

      // Verify research button has proper click handler
      expect(template.innerHTML).toContain('@click="research(message)"');

      // Verify research button has proper disabled state
      expect(template.innerHTML).toContain(
        ':disabled="isResearching(message)"'
      );

      // Verify research button shows proper text based on state
      expect(template.innerHTML).toContain(
        "x-text=\"isResearching(message) ? 'Researching...' : (message.research_completed_at ? 'Redo research' : 'Research!')\""
      );

      // Verify loading spinner shows during research
      expect(template.innerHTML).toContain(
        'x-show="isResearching(message)" class="loading-spinner"'
      );

      // Verify research status display
      expect(template.innerHTML).toContain(
        'x-text="getResearchStatusText(message)"'
      );
      expect(template.innerHTML).toContain(
        ':class="getResearchStatusClass(message)"'
      );
    }
  });

  it("should have Generate Reply button properly wired", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");
      expect(template).toBeTruthy();

      // Verify Generate Reply button exists and is properly wired
      // Should call generateReply(message) instead of console.log
      expect(template.innerHTML).toContain("Generate Reply");
      expect(template.innerHTML).toContain('@click="generateReply(message)"');

      // Should not have console.log placeholder
      expect(template.innerHTML).not.toContain("console.log('Generate reply");
    }
  });

  it("should have Archive button properly wired", () => {
    const dashboardView = document.getElementById("daily-dashboard-view");
    const messageList = dashboardView.querySelector(".message-list");

    if (messageList) {
      const template = messageList.querySelector("template");
      expect(template).toBeTruthy();

      // Verify Archive button exists and is properly wired
      // Should call archive with message_id instead of company
      expect(template.innerHTML).toContain("Archive");
      expect(template.innerHTML).toContain(
        '@click="archive(message.message_id)"'
      );

      // Should not have console.log placeholder
      expect(template.innerHTML).not.toContain("console.log('Archive for:");
    }
  });
});
