// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages

import { EmailScanningService } from "./email-scanning.js";
import { TaskPollingService } from "./task-polling.js";
import { formatMessageDate, showError, showSuccess } from "./ui-utils.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("dailyDashboard", () => {
    const emailScanningService = new EmailScanningService();
    const taskPollingService = new TaskPollingService();

    return {
      // Message list data
      unprocessedMessages: [],
      loading: false,

      // Sorting state
      sortNewestFirst: true,

      // Email scanning state - now managed by service
      doResearch: false, // User option to enable/disable research during scan

      // Message expansion state
      expandedMessages: new Set(), // Track which messages are expanded by company_id

      // Initialize the component
      async init() {
        console.log("Initializing daily dashboard component");
        await this.loadUnprocessedMessages();
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
      },

      // Get sort button text
      getSortButtonText() {
        return this.sortNewestFirst ? "Newest First" : "Oldest First";
      },

      // Load unprocessed messages from the messages endpoint
      async loadUnprocessedMessages() {
        this.loading = true;
        try {
          const response = await fetch("/api/messages");
          if (!response.ok) {
            throw new Error(`Failed to load messages: ${response.status}`);
          }

          const messages = await response.json();

          // Filter for unprocessed messages
          // Unprocessed = not archived and not replied to
          this.unprocessedMessages = messages.filter((message) => {
            return !message.archived_at;
          });

          console.log(
            `Loaded ${this.unprocessedMessages.length} unprocessed messages`
          );
        } catch (error) {
          console.error("Failed to load unprocessed messages:", error);
          // Could add user notification here
        } finally {
          this.loading = false;
        }
      },

      // Navigation method
      navigateToCompany(companyId) {
        // Switch to company management view and load company
        const companyList = Alpine.store('companyList');
        if (companyList) {
          companyList.navigateToCompany(companyId);
        }
      },

      // Research a company - follows same pattern as companies dashboard
      async research(message) {
        try {
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
        } catch (err) {
          console.error("Failed to research company:", err);
          // Could add user notification here
        } finally {
          taskPollingService.removeResearching(message);
        }
      },

      // Poll research status using the shared service
      pollResearchStatus: (message) =>
        taskPollingService.pollResearchStatus(message),

      // Get research status text using the shared service
      getResearchStatusText: (message) =>
        taskPollingService.getResearchStatusText(message),

      // Get research status CSS classes using the shared service
      getResearchStatusClass: (message) =>
        taskPollingService.getResearchStatusClass(message),

      // Check if company is being researched using the shared service
      isResearching: (message) => taskPollingService.isResearching(message),

      // Generate reply functionality (similar to app.js)
      async generateReply(message) {
        try {
          // Check if message has content
          if (!message.message) {
            showError("No message content to reply to");
            return;
          }

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
        } catch (err) {
          console.error("Failed to generate reply:", err);
          showError(
            err.message || "Failed to generate reply. Please try again."
          );
        } finally {
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
          await this.loadUnprocessedMessages();

          showSuccess("Message archived successfully");
        } catch (err) {
          console.error("Failed to archive message:", err);
          showError(
            err.message || "Failed to archive message. Please try again."
          );
        }
      },

      // Poll message status using the shared service
      pollMessageStatus: (message) =>
        taskPollingService.pollMessageStatus(message),

      // Check if company is generating message using the shared service
      isGeneratingMessage: (message) =>
        taskPollingService.isGeneratingMessage(message),

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
        await this.loadUnprocessedMessages();
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
          await this.loadUnprocessedMessages();
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
        return emailScanningService