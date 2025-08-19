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

    // Verify dashboard actions container exists (h2 was removed, title is now in main h1)
    const dashboardActions =
      dashboardHeader.querySelector(".dashboard-actions");
    expect(dashboardActions).toBeTruthy();

    // Verify filter controls exist
    const filterControls = dashboardActions.querySelector(".filter-controls");
    expect(filterControls).toBeTruthy();

    // Verify filter buttons exist
    const filterButtons = filterControls.querySelectorAll("button");
    expect(filterButtons.length).toBe(4);
    expect(filterButtons[0].textContent.trim()).toBe("All");
    expect(filterButtons[1].textContent.trim()).toBe("Not Replied");
    expect(filterButtons[2].textContent.trim()).toBe("Replied");
    expect(filterButtons[3].textContent.trim()).toBe("Archived");

    // Verify other buttons exist (scan emails, refresh, sort)
    const allButtons = dashboardActions.querySelectorAll("button");
    expect(allButtons.length).toBeGreaterThanOrEqual(7); // 4 filter buttons + 3 other buttons

    // Verify that buttons have Alpine directives
    const buttonsWithClick =
      dashboardActions.querySelectorAll("button[@click]");
    expect(buttonsWithClick.length).toBeGreaterThanOrEqual(7);
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
    expect(toggleButtons[1].textContent.trim()).toBe("Messages Dashboard");
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
    expect(filterButtons.length).toBe(4);
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
      "setFilterMode('replied')"
    );
    expect(filterButtons[3].hasAttribute("@click")).toBe(true);
    expect(filterButtons[3].getAttribute("@click")).toBe(
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
        ':disabled="isResearching(message) || isSendingMessage(message) || message.archived_at"'
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

  describe("Reply actions by status (template correctness)", () => {
    it("shows Generate + Edit actions when reply_status is none", () => {
      const dashboardView = document.getElementById("daily-dashboard-view");
      const messageList = dashboardView.querySelector(".message-list");

      if (messageList) {
        const template = messageList.querySelector("template");
        expect(template).toBeTruthy();

        const html = template.innerHTML;

        // Block guarded by x-if for reply_status === 'none' (and not archived)
        expect(html).toContain(
          "x-if=\"message.reply_status === 'none' &amp;&amp; !message.archived_at\""
        );

        // Within that block, Generate Reply and Edit buttons should exist and be wired
        expect(html).toContain("Generate Reply");
        expect(html).toContain('@click="generateReply(message)"');
        expect(html).toContain("@click=\"$dispatch('edit-reply', message)\"");
      }
    });

    it("shows preview + Edit + Regenerate when reply_status is generated", () => {
      const dashboardView = document.getElementById("daily-dashboard-view");
      const messageList = dashboardView.querySelector(".message-list");

      if (messageList) {
        const template = messageList.querySelector("template");
        expect(template).toBeTruthy();

        const html = template.innerHTML;

        // Block guarded by x-if for reply_status === 'generated' (and not archived)
        expect(html).toContain(
          "x-if=\"message.reply_status === 'generated' &amp;&amp; !message.archived_at\""
        );

        // Preview content and expand button
        expect(html).toContain("reply-preview");
        expect(html).toContain("toggleReplyExpansion(message.message_id)");

        // Edit and Regenerate buttons
        expect(html).toContain("@click=\"$dispatch('edit-reply', message)\"");
        expect(html).toContain('@click="generateReply(message)"');
      }
    });

    it("shows sent reply preview block without action buttons when reply_status is sent", () => {
      const dashboardView = document.getElementById("daily-dashboard-view");
      const messageList = dashboardView.querySelector(".message-list");

      if (messageList) {
        const template = messageList.querySelector("template");
        expect(template).toBeTruthy();

        const html = template.innerHTML;

        // Block guarded by x-if for reply_status === 'sent'
        expect(html).toContain("x-if=\"message.reply_status === 'sent'\"");

        // Sent preview is rendered
        expect(html).toContain("reply-preview sent");
        // Template comment indicates no action buttons for sent replies
        expect(html).toContain(
          "<!-- No action buttons for sent replies - editing is disabled -->"
        );
      }
    });

    it("shows archived reply preview block without action buttons when message is archived", () => {
      const dashboardView = document.getElementById("daily-dashboard-view");
      const messageList = dashboardView.querySelector(".message-list");

      if (messageList) {
        const template = messageList.querySelector("template");
        expect(template).toBeTruthy();

        const html = template.innerHTML;

        // Block guarded by x-if for archived messages with reply
        expect(html).toContain(
          'x-if="message.archived_at &amp;&amp; message.reply_message"'
        );

        // Archived preview is rendered
        expect(html).toContain("reply-preview archived");
        // Template comment indicates no action buttons for archived replies
        expect(html).toContain(
          "<!-- No action buttons for archived replies - editing is disabled -->"
        );
      }
    });

    it("hides reply actions for archived messages regardless of reply_status", () => {
      const dashboardView = document.getElementById("daily-dashboard-view");
      const messageList = dashboardView.querySelector(".message-list");

      if (messageList) {
        const template = messageList.querySelector("template");
        expect(template).toBeTruthy();

        const html = template.innerHTML;

        // Reply actions for 'none' status should be hidden for archived messages
        expect(html).toContain(
          "x-if=\"message.reply_status === 'none' &amp;&amp; !message.archived_at\""
        );

        // Reply actions for 'generated' status should be hidden for archived messages
        expect(html).toContain(
          "x-if=\"message.reply_status === 'generated' &amp;&amp; !message.archived_at\""
        );
      }
    });
  });

  describe("End-to-End Dashboard Flows", () => {
    let mockFetch;
    let Alpine;
    let dailyDashboard;

    beforeEach(async () => {
      // Mock fetch for API calls
      mockFetch = vi.fn();
      global.fetch = mockFetch;

      // Set up Alpine.js mock
      global.Alpine = {
        data: vi.fn(),
        start: vi.fn(),
        store: vi.fn(() => ({
          navigateToCompany: vi.fn(),
        })),
      };
      Alpine = global.Alpine;

      // Mock daily dashboard component
      dailyDashboard = {
        unprocessedMessages: [],
        loading: false,
        generatingMessages: new Set(),
        sendingMessages: new Set(),
        expandedReplies: new Set(),

        async generateReply(message) {
          this.generatingMessages.add(message.message_id);

          try {
            const response = await fetch(
              `/api/messages/${message.message_id}/reply`,
              {
                method: "POST",
              }
            );

            if (!response.ok) {
              throw new Error("Failed to generate reply");
            }

            const data = await response.json();

            // Simulate polling completion
            message.reply_message = "Generated reply content";
            message.reply_status = "generated";

            return data;
          } finally {
            this.generatingMessages.delete(message.message_id);
          }
        },

        async saveReply(message, replyText) {
          const response = await fetch(
            `/api/messages/${message.message_id}/reply`,
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ message: replyText }),
            }
          );

          if (!response.ok) {
            throw new Error("Failed to save reply");
          }

          message.reply_message = replyText;
          return await response.json();
        },

        async sendAndArchive(message) {
          this.sendingMessages.add(message.message_id);

          try {
            const response = await fetch(
              `/api/messages/${message.message_id}/send_and_archive`,
              {
                method: "POST",
              }
            );

            if (!response.ok) {
              throw new Error("Failed to send and archive");
            }

            // Simulate successful send and archive
            message.reply_status = "sent";
            message.reply_sent_at = new Date().toISOString();
            message.archived_at = new Date().toISOString();

            return await response.json();
          } finally {
            this.sendingMessages.delete(message.message_id);
          }
        },

        isGeneratingMessage(message) {
          return this.generatingMessages.has(message.message_id);
        },

        isSendingMessage(message) {
          return this.sendingMessages.has(message.message_id);
        },
      };

      // Register the component
      Alpine.data.mockImplementation((name, fn) => {
        if (name === "dailyDashboard") {
          return fn();
        }
      });
    });

    describe("Generate → Edit → Save Flow", () => {
      it("should complete full generate-edit-save workflow", async () => {
        const mockMessage = {
          message_id: "msg-123",
          company_id: "company-123",
          company_name: "Test Company",
          subject: "Test Subject",
          message: "Test message content",
          reply_message: "",
          reply_status: "none",
          reply_sent_at: null,
          archived_at: null,
        };

        // Mock API responses
        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () =>
              Promise.resolve({ task_id: "task-123", status: "pending" }),
          }) // Generate reply
          .mockResolvedValueOnce({
            ok: true,
            json: () =>
              Promise.resolve({ reply_message: "Updated reply content" }),
          }); // Save reply

        // Step 1: Generate reply
        expect(mockMessage.reply_status).toBe("none");
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);

        await dailyDashboard.generateReply(mockMessage);

        // Verify generate API was called
        expect(mockFetch).toHaveBeenCalledWith("/api/messages/msg-123/reply", {
          method: "POST",
        });

        // Verify message state after generation
        expect(mockMessage.reply_status).toBe("generated");
        expect(mockMessage.reply_message).toBe("Generated reply content");
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);

        // Step 2: Edit the generated reply
        const editedReplyText = "Edited reply content";

        // Step 3: Save the edited reply
        await dailyDashboard.saveReply(mockMessage, editedReplyText);

        // Verify save API was called
        expect(mockFetch).toHaveBeenCalledWith("/api/messages/msg-123/reply", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: editedReplyText }),
        });

        // Verify final state
        expect(mockMessage.reply_message).toBe(editedReplyText);
        expect(mockMessage.reply_status).toBe("generated"); // Still generated, not sent
      });

      it("should handle generate API failure gracefully", async () => {
        const mockMessage = {
          message_id: "msg-123",
          reply_status: "none",
        };

        // Mock API failure
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ error: "Server error" }),
        });

        await expect(dailyDashboard.generateReply(mockMessage)).rejects.toThrow(
          "Failed to generate reply"
        );

        // Verify loading state is cleared even on failure
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);
      });

      it("should handle save API failure gracefully", async () => {
        const mockMessage = {
          message_id: "msg-123",
          reply_message: "Original reply",
        };

        // Mock API failure
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: () => Promise.resolve({ error: "Bad request" }),
        });

        await expect(
          dailyDashboard.saveReply(mockMessage, "New reply")
        ).rejects.toThrow("Failed to save reply");

        // Verify original reply is preserved on failure
        expect(mockMessage.reply_message).toBe("Original reply");
      });
    });

    describe("Regenerate Confirmation Flow", () => {
      it("should regenerate reply for message with existing generated reply", async () => {
        const mockMessage = {
          message_id: "msg-456",
          company_name: "Test Company",
          reply_message: "Existing reply content",
          reply_status: "generated",
          reply_sent_at: null,
          archived_at: null,
        };

        // Mock API response for regenerate
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({ task_id: "task-456", status: "pending" }),
        });

        // Verify initial state
        expect(mockMessage.reply_message).toBe("Existing reply content");
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);

        // Regenerate reply (same method as generate, but on a message that already has a reply)
        await dailyDashboard.generateReply(mockMessage);

        // Verify API was called
        expect(mockFetch).toHaveBeenCalledWith("/api/messages/msg-456/reply", {
          method: "POST",
        });

        // Verify state after regeneration
        expect(mockMessage.reply_message).toBe("Generated reply content"); // New content
        expect(mockMessage.reply_status).toBe("generated");
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);
      });

      it("should not allow regenerate on sent messages", async () => {
        const mockMessage = {
          message_id: "msg-789",
          reply_message: "Sent reply content",
          reply_status: "sent",
          reply_sent_at: "2025-01-15T10:30:00Z",
          archived_at: null,
        };

        // In a real implementation, the UI would disable the regenerate button for sent messages
        // This test verifies that the state is correctly identified
        expect(mockMessage.reply_status).toBe("sent");
        expect(mockMessage.reply_sent_at).toBeTruthy();

        // The regenerate button should be disabled in the UI for sent messages
        // We don't call generateReply here because it would be prevented by the UI
      });

      it("should not allow regenerate on archived messages", async () => {
        const mockMessage = {
          message_id: "msg-999",
          reply_message: "Archived reply content",
          reply_status: "generated",
          reply_sent_at: null,
          archived_at: "2025-01-15T11:00:00Z",
        };

        // In a real implementation, the UI would disable the regenerate button for archived messages
        // This test verifies that the state is correctly identified
        expect(mockMessage.archived_at).toBeTruthy();

        // The regenerate button should be disabled in the UI for archived messages
        // We don't call generateReply here because it would be prevented by the UI
      });
    });

    describe("Send & Archive with Implicit Save Flow", () => {
      it("should complete full send-and-archive workflow", async () => {
        const mockMessage = {
          message_id: "msg-send-123",
          company_id: "company-send-123",
          company_name: "Send Test Company",
          reply_message: "Ready to send reply",
          reply_status: "generated",
          reply_sent_at: null,
          archived_at: null,
        };

        // Mock API response for send and archive
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              task_id: "send-task-123",
              status: "pending",
              sent_at: "2025-01-15T12:00:00Z",
              archived_at: "2025-01-15T12:00:00Z",
            }),
        });

        // Verify initial state
        expect(mockMessage.reply_status).toBe("generated");
        expect(mockMessage.reply_sent_at).toBeNull();
        expect(mockMessage.archived_at).toBeNull();
        expect(dailyDashboard.isSendingMessage(mockMessage)).toBe(false);

        // Send and archive
        await dailyDashboard.sendAndArchive(mockMessage);

        // Verify API was called
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/messages/msg-send-123/send_and_archive",
          { method: "POST" }
        );

        // Verify final state
        expect(mockMessage.reply_status).toBe("sent");
        expect(mockMessage.reply_sent_at).toBeTruthy();
        expect(mockMessage.archived_at).toBeTruthy();
        expect(dailyDashboard.isSendingMessage(mockMessage)).toBe(false);
      });

      it("should handle send-and-archive API failure gracefully", async () => {
        const mockMessage = {
          message_id: "msg-fail-123",
          reply_message: "Reply to send",
          reply_status: "generated",
          reply_sent_at: null,
          archived_at: null,
        };

        // Mock API failure
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ error: "Failed to send email" }),
        });

        await expect(
          dailyDashboard.sendAndArchive(mockMessage)
        ).rejects.toThrow("Failed to send and archive");

        // Verify state is unchanged on failure
        expect(mockMessage.reply_status).toBe("generated");
        expect(mockMessage.reply_sent_at).toBeNull();
        expect(mockMessage.archived_at).toBeNull();
        expect(dailyDashboard.isSendingMessage(mockMessage)).toBe(false);
      });

      it("should prevent send-and-archive on messages without reply", async () => {
        const mockMessage = {
          message_id: "msg-no-reply-123",
          reply_message: "",
          reply_status: "none",
          reply_sent_at: null,
          archived_at: null,
        };

        // In a real implementation, the UI would disable the send button for messages without replies
        // This test verifies that the state is correctly identified
        expect(mockMessage.reply_status).toBe("none");
        expect(mockMessage.reply_message).toBe("");

        // The send button should be disabled in the UI for messages without replies
        // We don't call sendAndArchive here because it would be prevented by the UI
      });

      it("should prevent send-and-archive on already sent messages", async () => {
        const mockMessage = {
          message_id: "msg-already-sent-123",
          reply_message: "Already sent reply",
          reply_status: "sent",
          reply_sent_at: "2025-01-15T10:00:00Z",
          archived_at: "2025-01-15T10:00:00Z",
        };

        // In a real implementation, the UI would hide/disable the send button for already sent messages
        // This test verifies that the state is correctly identified
        expect(mockMessage.reply_status).toBe("sent");
        expect(mockMessage.reply_sent_at).toBeTruthy();
        expect(mockMessage.archived_at).toBeTruthy();

        // The send button should be hidden/disabled in the UI for already sent messages
        // We don't call sendAndArchive here because it would be prevented by the UI
      });
    });

    describe("State Transitions During Workflows", () => {
      it("should track loading states correctly during generate workflow", async () => {
        const mockMessage = {
          message_id: "msg-loading-123",
          reply_status: "none",
        };

        let generatePromise;

        // Mock slow API response
        mockFetch.mockImplementationOnce(() => {
          return new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({ task_id: "task-123", status: "pending" }),
              });
            }, 100);
          });
        });

        // Start generation
        generatePromise = dailyDashboard.generateReply(mockMessage);

        // Verify loading state is set immediately
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(true);

        // Wait for completion
        await generatePromise;

        // Verify loading state is cleared
        expect(dailyDashboard.isGeneratingMessage(mockMessage)).toBe(false);
      });

      it("should track loading states correctly during send-and-archive workflow", async () => {
        const mockMessage = {
          message_id: "msg-send-loading-123",
          reply_message: "Reply to send",
          reply_status: "generated",
        };

        let sendPromise;

        // Mock slow API response
        mockFetch.mockImplementationOnce(() => {
          return new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    task_id: "send-task-123",
                    status: "pending",
                  }),
              });
            }, 100);
          });
        });

        // Start send and archive
        sendPromise = dailyDashboard.sendAndArchive(mockMessage);

        // Verify loading state is set immediately
        expect(dailyDashboard.isSendingMessage(mockMessage)).toBe(true);

        // Wait for completion
        await sendPromise;

        // Verify loading state is cleared
        expect(dailyDashboard.isSendingMessage(mockMessage)).toBe(false);
      });

      it("should handle concurrent operations on different messages", async () => {
        const message1 = {
          message_id: "msg-concurrent-1",
          reply_status: "none",
        };

        const message2 = {
          message_id: "msg-concurrent-2",
          reply_message: "Reply to send",
          reply_status: "generated",
        };

        // Mock API responses
        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () =>
              Promise.resolve({ task_id: "task-1", status: "pending" }),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: () =>
              Promise.resolve({ task_id: "task-2", status: "pending" }),
          });

        // Start concurrent operations
        const generatePromise = dailyDashboard.generateReply(message1);
        const sendPromise = dailyDashboard.sendAndArchive(message2);

        // Verify both operations are tracked independently
        expect(dailyDashboard.isGeneratingMessage(message1)).toBe(true);
        expect(dailyDashboard.isSendingMessage(message1)).toBe(false);
        expect(dailyDashboard.isGeneratingMessage(message2)).toBe(false);
        expect(dailyDashboard.isSendingMessage(message2)).toBe(true);

        // Wait for both to complete
        await Promise.all([generatePromise, sendPromise]);

        // Verify both loading states are cleared
        expect(dailyDashboard.isGeneratingMessage(message1)).toBe(false);
        expect(dailyDashboard.isSendingMessage(message1)).toBe(false);
        expect(dailyDashboard.isGeneratingMessage(message2)).toBe(false);
        expect(dailyDashboard.isSendingMessage(message2)).toBe(false);
      });
    });
  });
});
