// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages
//
// Note: Reply drafts are currently stored at the company level (Company.reply_message).
// If a company has multiple messages, editing/generating a reply for one message
// will update the company's shared reply draft. This is a temporary limitation
// until per-message draft storage is implemented.

import { CompaniesService } from "./companies-service.js";
import {
  // buildUpdatedSearch,
  filterMessages,
  // parseUrlState,
  sortMessages,
  getFilterHeading as utilGetFilterHeading,
} from "./dashboard-utils.js";
import { EmailScanningService } from "./email-scanning.js";
import { computeMessagePreview } from "./message-utils.js";
import { TaskPollingService } from "./task-polling.js";
import {
  confirmDialogs,
  errorLogger,
  formatMessageDate,
  showError,
  showSuccess,
} from "./ui-utils.js";
import { readDailyDashboardStateFromUrl, updateDailyDashboardUrlWithState } from "./url-utils.js";

document.addEventListener("alpine:init", () => {
  const emailScanningService = new EmailScanningService();
  const taskPollingService = new TaskPollingService();

  // Make services available globally for methods
  window.emailScanningService = emailScanningService;

  Alpine.data("dailyDashboard", () => {
    const companiesService = new CompaniesService();
    return {
      // Message list data
      unprocessedMessages: [],
      loading: false,

      // Filtering state - REPLACED with filterMode approach
      filterMode: "all", // 'all', 'archived', 'replied', 'not-replied'

      // Local tracking for UI state
      generatingMessages: new Set(),
      researchingCompanies: new Set(),
      sendingMessages: new Set(), // Track messages being sent and archived

      // Sorting state
      sortNewestFirst: true,

      // Email scanning state - now managed by service
      doResearch: false, // User option to enable/disable research during scan

      // Message expansion state
      expandedMessages: new Set(), // Track which messages are expanded by company_id
      expandedReplies: new Set(), // Track which replies are expanded by message_id

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
        const { filterMode, sortNewestFirst } = readDailyDashboardStateFromUrl(
          window.location.search
        );
        this.filterMode = filterMode;
        this.sortNewestFirst = sortNewestFirst;
      },

      // Update URL with current filtering state
      updateUrlWithFilterState() {
        updateDailyDashboardUrlWithState(
          this.filterMode,
          this.sortNewestFirst
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
        return sortMessages(this.unprocessedMessages, this.sortNewestFirst);
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
          const messages = await companiesService.getMessages();

          // Apply client-side filtering based on filterMode
          this.unprocessedMessages = filterMessages(messages, this.filterMode);

          console.log(
            `Loaded ${this.unprocessedMessages.length} messages after filtering (mode: ${this.filterMode})`
          );
        } catch (error) {
          errorLogger.logFailedTo("load messages", error);
          showError(
            "Failed to load messages. Please refresh the page to try again."
          );
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
          this.researchingCompanies.add(message.company_name);
          taskPollingService.addResearching(message);
          const data = await companiesService.research(message.company_id);
          message.research_task_id = data.task_id;
          message.research_status = data.status;

          await this.pollResearchStatus(message);

          await this.loadMessages();
          showSuccess("Company research completed!");
        } catch (err) {
          errorLogger.logFailedTo("research company", err);
          showError(
            err.message || "Failed to research company. Please try again."
          );
        } finally {
          this.researchingCompanies.delete(message.company_name);
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
        return this.researchingCompanies.has(message.company_name);
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
          this.generatingMessages.add(message.message_id);
          // Also add to service for polling
          taskPollingService.addGeneratingMessage(message);

          const data = await companiesService.generateReply(message.message_id);
          message.message_task_id = data.task_id;
          message.message_status = data.status;

          // Start polling for updates
          await this.pollMessageStatus(message);

          // Refresh the message list after generation
          await this.loadMessages();
          showSuccess("Reply generated successfully!");
        } catch (err) {
          errorLogger.logFailedTo("generate reply", err);
          showError(
            err.message || "Failed to generate reply. Please try again."
          );
        } finally {
          this.generatingMessages.delete(message.message_id);
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
        if (!confirmDialogs.archiveWithoutReply()) {
          return;
        }

        try {
          // Call the message-centric archive endpoint via service
          await companiesService.archiveMessage(message_id);

          // Refresh the message list to remove the archived message
          await this.loadMessages();

          showSuccess("Message archived successfully");
        } catch (err) {
          errorLogger.logFailedTo("archive message", err);
          showError(
            err.message || "Failed to archive message. Please try again."
          );
        }
      },

      // Send and archive a message - uses message-centric endpoint
      async sendAndArchive(message) {
        console.log("sendAndArchive called with message:", message);

        if (!message || !message.message_id) {
          showError("No message provided");
          return;
        }

        if (!message.reply_message) {
          showError("No reply message to send");
          return;
        }

        // Confirm with the user before proceeding
        console.log("About to show confirmation dialog");
        if (!confirmDialogs.sendAndArchive()) {
          console.log("User cancelled confirmation");
          return;
        }
        console.log("User confirmed, proceeding with send and archive");

        // Add to local tracking for immediate UI update - do this BEFORE any API calls
        this.sendingMessages.add(message.message_id);
        // Also add to service for polling
        taskPollingService.addSendingMessage(message);

        try {
          // First check if there's an active edit session and save it
          const companyListElement = document.querySelector(
            '[x-data="companyList"]'
          );
          if (companyListElement && companyListElement._x_dataStack) {
            const companyList = companyListElement._x_dataStack[0];

            // Check if we're currently editing this message's reply
            if (
              companyList.editingCompany &&
              companyList.editingCompany.recruiter_message?.message_id ===
                message.message_id &&
              companyList.editingReply !== message.reply_message
            ) {
              // Save the current draft first
              companyList.editingCompany.reply_message =
                companyList.editingReply;
              await companyList.saveReply();

              // Refresh the message list to get the updated reply
              await this.loadMessages();
            }
          }

          // Call the message-centric send and archive endpoint via service
          const data = await companiesService.sendAndArchive(
            message.message_id
          );
          console.log("Send and archive response:", data);

          // Poll for task completion before showing success/failure
          console.log("Polling for task completion...");
          try {
            const taskResult =
              await taskPollingService.pollSendAndArchiveStatus(data.task_id);
            console.log("Task completed:", taskResult);

            // Refresh the message list to reflect the changes
            console.log("Refreshing message list...");
            await this.loadMessages();
            console.log("Message list refreshed successfully");

            // Show appropriate alert based on actual task result
            if (taskResult.status === "completed") {
              showSuccess("Reply sent and message archived successfully");
            } else {
              showError(
                `Failed to send and archive: ${
                  taskResult.error || "Unknown error"
                }`
              );
            }
          } catch (pollError) {
            errorLogger.logFailedTo("poll task status", pollError);
            showError(
              "Failed to check task status. Please refresh to see current state."
            );
          }
        } catch (err) {
          errorLogger.logFailedTo("send and archive message", err);
          showError(
            err.message ||
              "Failed to send and archive message. Please try again."
          );
        } finally {
          this.sendingMessages.delete(message.message_id);
          taskPollingService.removeSendingMessage(message);
        }
      },

      // Poll message status using the shared service
      async pollMessageStatus(message) {
        return await taskPollingService.pollMessageStatus(message);
      },

      // Check if company is generating message using the shared service
      isGeneratingMessage(message) {
        if (!message) return false;
        return this.generatingMessages.has(message.message_id);
      },

      // Check if message is being sent and archived
      isSendingMessage(message) {
        if (!message) return false;
        return this.sendingMessages.has(message.message_id);
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
          errorLogger.logFailedTo("scan recruiter emails", err);
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

      // Toggle reply expansion
      toggleReplyExpansion(messageId) {
        if (this.expandedReplies.has(messageId)) {
          this.expandedReplies.delete(messageId);
        } else {
          this.expandedReplies.add(messageId);
        }
      },

      // Get reply expand button text
      getReplyExpandButtonText(messageId) {
        return this.expandedReplies.has(messageId) ? "Show Less" : "Show More";
      },

      // Get filter heading based on current filter mode
      getFilterHeading() {
        // Defensive check for test environments
        if (!this.unprocessedMessages || !this.filterMode) {
          return "Messages (0)";
        }
        return utilGetFilterHeading(
          this.filterMode,
          this.unprocessedMessages.length
        );
      },
    };
  });
});
