// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages

import { EmailScanningService } from "./email-scanning.js";
import { TaskPollingService } from "./task-polling.js";
import { formatMessageDate } from "./ui-utils.js";

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

      // Load unprocessed messages from the companies endpoint
      async loadUnprocessedMessages() {
        this.loading = true;
        try {
          const response = await fetch("/api/companies");
          if (!response.ok) {
            throw new Error(`Failed to load companies: ${response.status}`);
          }

          const companies = await response.json();

          // Filter for companies with unprocessed recruiter messages
          // Unprocessed = has recruiter message but not replied to or archived
          this.unprocessedMessages = companies.filter((company) => {
            return (
              company.recruiter_message &&
              !company.sent_at &&
              !company.archived_at
            );
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

      // Research a company - follows same pattern as companies dashboard
      async research(company) {
        try {
          taskPollingService.addResearching(company);
          const response = await fetch(
            `/api/companies/${company.company_id}/research`,
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
          company.research_task_id = data.task_id;
          company.research_status = data.status;

          await this.pollResearchStatus(company);
        } catch (err) {
          console.error("Failed to research company:", err);
          // Could add user notification here
        } finally {
          taskPollingService.removeResearching(company);
        }
      },

      // Poll research status using the shared service
      pollResearchStatus: (company) =>
        taskPollingService.pollResearchStatus(company),

      // Get research status text using the shared service
      getResearchStatusText: (company) =>
        taskPollingService.getResearchStatusText(company),

      // Get research status CSS classes using the shared service
      getResearchStatusClass: (company) =>
        taskPollingService.getResearchStatusClass(company),

      // Check if company is being researched using the shared service
      isResearching: (company) => taskPollingService.isResearching(company),

      formatMessageDate,

      // Get company name or fallback
      getCompanyName(company) {
        return company.name || "Unknown Company";
      },

      // Get message sender
      getMessageSender(company) {
        return company.recruiter_message?.sender || "Unknown Sender";
      },

      // Get message subject
      getMessageSubject(company) {
        return company.recruiter_message?.subject || "No Subject";
      },

      // Get message date
      getMessageDate(company) {
        return company.recruiter_message?.date || null;
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
        return emailScanningService.emailScanStatus;
      },

      // Toggle message expansion
      toggleMessageExpansion(companyId) {
        if (this.expandedMessages.has(companyId)) {
          this.expandedMessages.delete(companyId);
        } else {
          this.expandedMessages.add(companyId);
        }
      },

      // Check if message is expanded
      isMessageExpanded(companyId) {
        return this.expandedMessages.has(companyId);
      },

      // Get message preview text (truncated or full)
      getMessagePreview(company) {
        const message = company.recruiter_message?.message || "";
        if (this.isMessageExpanded(company.company_id)) {
          return message;
        }
        return message.length > 200
          ? message.substring(0, 200) + "..."
          : message;
      },

      // Get expand/collapse button text
      getExpandButtonText(companyId) {
        return this.isMessageExpanded(companyId) ? "Show Less" : "Show More";
      },
    };
  });
});
