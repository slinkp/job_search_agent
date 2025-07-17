// Daily Dashboard Component
// Handles the display and interaction with unprocessed recruiter messages

document.addEventListener("alpine:init", () => {
  Alpine.data("dailyDashboard", () => {
    return {
      // Message list data
      unprocessedMessages: [],
      loading: false,

      // Initialize the component
      async init() {
        console.log("Initializing daily dashboard component");
        await this.loadUnprocessedMessages();
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
    };
  });
});
