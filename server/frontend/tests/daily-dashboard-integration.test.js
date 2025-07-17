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

    // Verify refresh button exists
    const refreshButton = dashboardHeader.querySelector("button");
    expect(refreshButton).toBeTruthy();
    expect(refreshButton.textContent).toContain("Refresh");
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
});
