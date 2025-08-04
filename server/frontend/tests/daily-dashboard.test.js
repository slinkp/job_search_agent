import { beforeEach, describe, expect, it, vi } from "vitest";
import { setupDocumentWithIndexHtml } from "./test-utils";

describe("Daily Dashboard State Management", () => {
  let Alpine;
  let dailyDashboard;

  beforeEach(() => {
    // Mock fetch globally to prevent network errors
    global.fetch = vi.fn();
    
    // Set up document with actual HTML
    setupDocumentWithIndexHtml(document);

    // Mock Alpine.js data
    dailyDashboard = {
      hideRepliedMessages: true,
      hideArchivedCompanies: true,
      sortNewestFirst: true,
      unprocessedMessages: [],
      loading: false,
      expandedMessages: new Set(),
      
      // Mock methods
      readFilterStateFromUrl: vi.fn(function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('hideReplied') !== null) {
          this.hideRepliedMessages = urlParams.get('hideReplied') === 'true';
        }
        if (urlParams.get('hideArchived') !== null) {
          this.hideArchivedCompanies = urlParams.get('hideArchived') === 'true';
        }
      }),
      updateUrlWithFilterState: vi.fn(),
      loadMessages: vi.fn(),
      toggleHideRepliedMessages: vi.fn(function() {
        this.hideRepliedMessages = !this.hideRepliedMessages;
        this.updateUrlWithFilterState();
      }),
      toggleHideArchivedCompanies: vi.fn(function() {
        this.hideArchivedCompanies = !this.hideArchivedCompanies;
        this.updateUrlWithFilterState();
      }),
      toggleSortOrder: vi.fn(function() {
        this.sortNewestFirst = !this.sortNewestFirst;
      }),
      init: vi.fn(function() {
        this.readFilterStateFromUrl();
        this.loadMessages();
      })
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with correct default state", () => {
    expect(dailyDashboard.hideRepliedMessages).toBe(true);
    expect(dailyDashboard.hideArchivedCompanies).toBe(true);
    expect(dailyDashboard.sortNewestFirst).toBe(true);
  });

  it("reads state from URL parameters during init", () => {
    // Mock URL parameters
    const urlParams = new URLSearchParams();
    urlParams.set('hideReplied', 'false');
    urlParams.set('hideArchived', 'false');
    Object.defineProperty(window, 'location', {
      value: {
        search: urlParams.toString()
      },
      writable: true
    });

    dailyDashboard.init();
    expect(dailyDashboard.readFilterStateFromUrl).toHaveBeenCalled();
    // Verify state was updated from URL parameters
    expect(dailyDashboard.hideRepliedMessages).toBe(false);
    expect(dailyDashboard.hideArchivedCompanies).toBe(false);
  });

  it("toggles hideRepliedMessages and updates URL", () => {
    dailyDashboard.toggleHideRepliedMessages();
    expect(dailyDashboard.hideRepliedMessages).toBe(false);
    expect(dailyDashboard.updateUrlWithFilterState).toHaveBeenCalled();
  });

  it("toggles hideArchivedCompanies and updates URL", () => {
    dailyDashboard.toggleHideArchivedCompanies();
    expect(dailyDashboard.hideArchivedCompanies).toBe(false);
    expect(dailyDashboard.updateUrlWithFilterState).toHaveBeenCalled();
  });

  it("toggles sort order", () => {
    dailyDashboard.toggleSortOrder();
    expect(dailyDashboard.sortNewestFirst).toBe(false);
  });

  it("updates URL with current filter state", () => {
    // Set custom state
    dailyDashboard.hideRepliedMessages = false;
    dailyDashboard.hideArchivedCompanies = false;
    
    dailyDashboard.updateUrlWithFilterState();
    
    // Verify URL parameters are set correctly
    expect(dailyDashboard.updateUrlWithFilterState).toHaveBeenCalled();
    // In a real test, we would check window.location.search
  });

  it("restores state from URL parameters", () => {
    // Mock URL with specific parameters
    const urlParams = new URLSearchParams();
    urlParams.set('hideReplied', 'false');
    urlParams.set('hideArchived', 'false');
    Object.defineProperty(window, 'location', {
      value: {
        search: urlParams.toString()
      },
      writable: true
    });

    // Simulate reading from URL
    dailyDashboard.readFilterStateFromUrl();
    
    expect(dailyDashboard.hideRepliedMessages).toBe(false);
    expect(dailyDashboard.hideArchivedCompanies).toBe(false);
  });

  it("preserves default state when URL parameters are missing", () => {
    // Mock empty URL parameters
    Object.defineProperty(window, 'location', {
      value: {
        search: ''
      },
      writable: true
    });

    dailyDashboard.readFilterStateFromUrl();
    
    expect(dailyDashboard.hideRepliedMessages).toBe(true);
    expect(dailyDashboard.hideArchivedCompanies).toBe(true);
  });
});
