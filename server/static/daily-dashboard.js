// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages

import { EmailScanningService } from "./email-scanning.js";
import { computeMessagePreview } from "./message-utils.js";
import { TaskPollingService } from "./task-polling.js";
import { formatMessageDate, showError, showSuccess } from "./ui-utils.js";

document.addEventListener("alpine:init", () => {
  const emailScanningService = new EmailScanningService();
  const taskPollingService = new TaskPollingService();

  // Make services available globally for methods
  window.emailScanningService = emailScanningService;

  Alpine.data("dailyDashboard", () => {
    return {
      // Message list data
      unprocessedMessages: [],
      loading: false,

      // Filtering state - REPLACED with filterMode approach
      filterMode: "all", // 'all', 'archived', 'replied', 'not-replied'

      // Local tracking for UI state
      generatingMessages: new Set(),
      researchingCompanies: new Set(),

      // Sorting state
      sortNewestFirst: true,

      // Email scanning state - now managed by service
      doResearch: false, // User option to enable/disable research during scan

      // Message expansion state
      expandedMessages: new Set(), // Track which messages are expanded by company_id

      // Initialize the component
      async init() {
        console.log("Initializing daily dashboard component");
        // Read filtering state from URL
        this.readFilterStateFromUrl();
        await this.loadMessages();

        // Handle anchor scrolling after messages load
        this.$nextTick(() => {
          if (window.location.hash) {
            const element = document.getElementById(
              window.location.hash.slice(1)
            );
            if (element) {
              element.scrollIntoView({ behavior: "smooth" });
            }
          }
        });
      },

      // Read filtering state from URL parameters
      readFilterStateFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);

        // Read filterMode state
        const filterModeParam = urlParams.get("filterMode");
        if (filterModeParam) {
          this.filterMode = filterModeParam;
        }

        // New: Read sort order from URL
        const sortParam = urlParams.get("sort");
        if (sortParam) {
          this.sortNewestFirst = sortParam === "newest";
        }
      },

      // Update URL with current filtering state
      updateUrlWithFilterState() {
        // Preserve existing parameters while updating filter state
        const params = new URLSearchParams(window.location.search);

        // Update filter values
        params.set("filterMode", this.filterMode);
        params.set("sort", this.sortNewestFirst ? "newest" : "oldest");

        // Preserve hash and path
        const hash = window.location.hash;
        const path = window.location.pathname || "/";

        // Build new URL with updated search params while preserving existing ones
        const newUrl = `${path}?${params.toString()}${hash}`.replace(
          /([^:])\/\//g,
          "$1/"
        );

        // Update history without reloading
        window.history.replaceState(
          { ...window.history.state, filtersUpdated: true },
          "",
          newUrl
        );
      },

      // Set filter mode
      setFilterMode(mode) {
        this.filterMode = mode;
        this.updateUrlWithFilterState();
        this.loadMessages();
      },

      // Computed property for sorted messages
      get sortedMessages() {
        if (!this.unprocessedMessages.length) return [];

        return [...this.unprocessedMessages].sort((a, b) => {
          const dateA = this.getMessageDate(a);
          const dateB = this.getMessageDate(b);

          // Handle cases where date might be null
          if (!dateA && !dateB) return 0;
          if (!dateA) return 1;
          if (!dateB) return -1;

          const timeA = new Date(dateA).getTime();
          const timeB = new Date(dateB).getTime();

          return this.sortNewestFirst ? timeB - timeA : timeA - timeB;
        });
      },

      // Toggle sort order
      toggleSortOrder() {
        this.sortNewestFirst = !this.sortNewestFirst;
        this.updateUrlWithFilterState(); // Now updates URL
      },

      // Get sort button text
      getSortButtonText() {
        return this.sortNewestFirst ? "Newest First" : "Oldest First";
      },

      // Load messages from the messages endpoint and apply client-side filtering
      async loadMessages() {
        this.loading = true;
        try {
          const response = await fetch("/api/messages");
          if (!response.ok) {
            throw new Error(`Failed to load messages: ${response.status}`);
          }

          const messages = await response.json();

          // Apply client-side filtering based on filterMode
          let filteredMessages = messages;

          switch (this.filterMode) {
            case "archived":
              // Show ONLY archived messages
              filteredMessages = filteredMessages.filter((message) => {
                return message.archived_at || message.company_archived_at;
              });
              break;
            case "replied":
              // Show ONLY replied messages
              filteredMessages = filteredMessages.filter((message) => {
                return message.reply_sent_at;
              });
              break;
            case "not-replied":
              // Show ONLY un-replied messages
              filteredMessages = filteredMessages.filter((message) => {
                return !message.reply_sent_at;
              });
              break;
            case "all":
            default:
              // Show all messages (no filtering)
              break;
          }

          this.unprocessedMessages = filteredMessages;

          console.log(
            `Loaded ${this.unprocessedMessages.length} messages after filtering (mode: ${this.filterMode})`
          );
        } catch (error) {
          console.error("Failed to load messages:", error);
          // Could add user notification here
        } finally {
          this.loading = false;
        }
      },

      // Navigation method
      navigateToCompany(companyId) {
        // Switch to company management view and load company
        const companyList = Alpine.store("companyList");
        if (companyList) {
          companyList.navigateToCompany(companyId);
        }
      },

      // Research a company - follows same pattern as companies dashboard
      async research(message) {
        try {
          this.researchingCompanies.add(message.name);
          taskPollingService.addResearching(message);
          const response = await fetch(
            `/api/companies/${message.company_id}/research`,
            {
              method: "POST",
            }
          );

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to start research: ${response.status}`
            );
          }

          const data = await response.json();
          message.research_task_id = data.task_id;
          message.research_status = data.status;

          await this.pollResearchStatus(message);

          await this.loadMessages();
          showSuccess("Company research completed!");
        } catch (err) {
          console.error("Failed to research company:", err);
          // Could add user notification here
        } finally {
          this.researchingCompanies.delete(message.name);
          taskPollingService.removeResearching(message);
        }
      },

      // Poll research status using the shared service
      async pollResearchStatus(message) {
        return await taskPollingService.pollResearchStatus(message);
      },

      // Get research status text using the shared service
      getResearchStatusText: (message) =>
        taskPollingService.getResearchStatusText(message),

      // Get research status CSS classes using the shared service
      getResearchStatusClass: (message) =>
        taskPollingService.getResearchStatusClass(message),

      // Check if company is being researched using the shared service
      isResearching(message) {
        if (!message) return false;
        return this.researchingCompanies.has(message.name);
      },

      // Generate reply functionality (similar to app.js)
      async generateReply(message) {
        try {
          // Check if message has content
          if (!message.message) {
            showError("No message content to reply to");
            return;
          }

          // Add to local tracking for immediate UI update
          this.generatingMessages.add(message.name);
          // Also add to service for polling
          taskPollingService.addGeneratingMessage(message);

          const response = await fetch(
            `/api/messages/${message.message_id}/reply`,
            {
              method: "POST",
            }
          );

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to generate reply: ${response.status}`
            );
          }

          const data = await response.json();
          message.message_task_id = data.task_id;
          message.message_status = data.status;

          // Start polling for updates
          await this.pollMessageStatus(message);

          // Refresh the message list after generation
          await this.loadMessages();
          showSuccess("Reply generated successfully!");
        } catch (err) {
          console.error("Failed to generate reply:", err);
          showError(
            err.message || "Failed to generate reply. Please try again."
          );
        } finally {
          this.generatingMessages.delete(message.name);
          taskPollingService.removeGeneratingMessage(message);
        }
      },

      // Archive a message without replying - follows same pattern as other actions
      async archive(message_id) {
        if (!message_id) {
          showError("No message ID provided");
          return;
        }

        // Confirm with the user before proceeding
        if (
          !confirm(
            "Are you sure you want to archive this message without replying?"
          )
        ) {
          return;
        }

        try {
          // Call the message-centric archive endpoint
          const response = await fetch(`/api/messages/${message_id}/archive`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to archive message: ${response.status}`
            );
          }

          // Refresh the message list to remove the archived message
          await this.loadMessages();

          showSuccess("Message archived successfully");
        } catch (err) {
          console.error("Failed to archive message:", err);
          showError(
            err.message || "Failed to archive message. Please try again."
          );
        }
      },

      // Poll message status using the shared service
      async pollMessageStatus(message) {
        return await taskPollingService.pollMessageStatus(message);
      },

      // Check if company is generating message using the shared service
      isGeneratingMessage(message) {
        if (!message) return false;
        return this.generatingMessages.has(message.name);
      },

      formatMessageDate,

      // Get company name or fallback
      getCompanyName(message) {
        return message.company_name || "Unknown Company";
      },

      // Get message sender
      getMessageSender(message) {
        return message.sender || "Unknown Sender";
      },

      // Get message subject
      getMessageSubject(message) {
        return message.subject || "No Subject";
      },

      // Get message date
      getMessageDate(message) {
        return message.date || null;
      },

      // Refresh the message list
      async refresh() {
        await this.loadMessages();
      },

      // Scan for new recruiter emails from Gmail
      async scanRecruiterEmails() {
        try {
          await emailScanningService.scanRecruiterEmails(this.doResearch);
          await this.pollEmailScanStatus();
        } catch (err) {
          console.error("Failed to scan recruiter emails:", err);
          // Error is already handled by the service
        }
      },

      // Poll for email scan task status
      async pollEmailScanStatus() {
        const result = await emailScanningService.pollEmailScanStatus();

        if (result?.status === "completed") {
          // Reload messages after successful scan
          await this.loadMessages();
        }
      },

      // Get email scan status text for display
      getEmailScanStatusText() {
        return emailScanningService.getEmailScanStatusText();
      },

      // Get email scan status CSS classes
      getEmailScanStatusClass() {
        return emailScanningService.getEmailScanStatusClass();
      },

      // Get scanning emails state from service
      get scanningEmails() {
        return emailScanningService.scanningEmails;
      },

      // Get email scan status from service
      get emailScanStatus() {
        return emailScanningService.emailScanStatus;
      },

      // Get message preview (first 200 characters)
      getMessagePreview(message) {
        return computeMessagePreview(
          message,
          this.expandedMessages.has(message.message_id)
        );
      },

      // Toggle message expansion
      toggleMessageExpansion(messageId) {
        if (this.expandedMessages.has(messageId)) {
          this.expandedMessages.delete(messageId);
        } else {
          this.expandedMessages.add(messageId);
        }
      },

      // Get expand button text
      getExpandButtonText(messageId) {
        return this.expandedMessages.has(messageId) ? "Show Less" : "Show More";
      },

      // Get filter heading based on current filter mode
      getFilterHeading() {
        // Defensive check for test environments
        if (!this.unprocessedMessages || !this.filterMode) {
          return "Messages (0)";
        }

        const count = this.unprocessedMessages.length;
        switch (this.filterMode) {
          case "all":
            return `All Messages (${count})`;
          case "not-replied":
            return `Unreplied Messages (${count})`;
          case "archived":
            return `Archived Messages (${count})`;
          case "replied":
            return `Replied Messages (${count})`;
          default:
            return `Messages (${count})`;
        }
      },
    };
  });
});
