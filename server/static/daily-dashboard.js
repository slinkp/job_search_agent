// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages

document.addEventListener("alpine:init", () => {
  Alpine.data("dailyDashboard", () => {
    return {
      // Message list data
      unprocessedMessages: [],
      loading: false,

      // Sorting state
      sortNewestFirst: true,

      // Email scanning state
      scanningEmails: false,
      emailScanTaskId: null,
      emailScanStatus: null,
      emailScanError: null,
      doResearch: false, // User option to enable/disable research during scan

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

      // Format message date for display
      formatMessageDate(dateString) {
        if (!dateString) return "Unknown date";
        try {
          const date = new Date(dateString);
          return (
            date.toLocaleDateString() +
            " " +
            date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          );
        } catch (error) {
          return "Invalid date";
        }
      },

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
        if (this.scanningEmails) return;

        try {
          this.scanningEmails = true;
          this.emailScanError = null;

          const response = await fetch("/api/scan_recruiter_emails", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              do_research: this.doResearch, // Use user preference instead of hardcoded false
            }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to scan emails: ${response.status}`
            );
          }

          const data = await response.json();
          this.emailScanTaskId = data.task_id;
          this.emailScanStatus = data.status;

          await this.pollEmailScanStatus();
        } catch (err) {
          console.error("Failed to scan recruiter emails:", err);
          this.emailScanError = err.message;
        } finally {
          this.scanningEmails = false;
        }
      },

      // Poll for email scan task status
      async pollEmailScanStatus() {
        if (!this.emailScanTaskId) return;

        try {
          const response = await fetch(`/api/tasks/${this.emailScanTaskId}`);
          if (!response.ok) {
            throw new Error(`Failed to get task status: ${response.status}`);
          }

          const task = await response.json();
          this.emailScanStatus = task.status;

          if (task.status === "completed") {
            console.log("Email scan completed successfully");
            // Reload messages after successful scan
            await this.loadUnprocessedMessages();
            this.emailScanTaskId = null;
          } else if (task.status === "failed") {
            console.error("Email scan failed:", task.result);
            this.emailScanError = task.result?.error || "Email scan failed";
            this.emailScanTaskId = null;
          } else if (task.status === "pending" || task.status === "running") {
            // Continue polling
            setTimeout(() => this.pollEmailScanStatus(), 2000);
          }
        } catch (err) {
          console.error("Failed to poll email scan status:", err);
          this.emailScanError = err.message;
          this.emailScanTaskId = null;
        }
      },

      // Get email scan status text for display
      getEmailScanStatusText() {
        if (this.emailScanError) {
          return `Failed: ${this.emailScanError}`;
        }
        switch (this.emailScanStatus) {
          case "pending":
            return "Starting email scan...";
          case "running":
            return "Scanning recruiter emails... (this may take a while for large fetches)";
          case "completed":
            return "Email scan complete";
          case "failed":
            return "Failed to scan emails";
          default:
            return "";
        }
      },

      // Get email scan status CSS classes
      getEmailScanStatusClass() {
        return {
          "status-pending": this.emailScanStatus === "pending",
          "status-running": this.emailScanStatus === "running",
          "status-completed": this.emailScanStatus === "completed",
          "status-failed": this.emailScanStatus === "failed",
        };
      },
    };
  });
});
