import { CompanyResearchService } from "./company-research.js";
import { EmailScanningService } from "./email-scanning.js";
import { TaskPollingService } from "./task-polling.js";
import {
  formatRecruiterMessageDate,
  isUrl,
  showError,
  showSuccess,
} from "./ui-utils.js";

// Add CSS for message date styling and status icons
const style = document.createElement("style");
style.textContent = `
  .message-date {
    font-size: 0.9em;
    font-weight: normal;
    color: #666;
  }
  
  .message-headers {
    margin-bottom: 10px;
    padding: 8px;
    background-color: #f5f5f5;
    border-radius: 4px;
  }
  
  .message-headers p {
    margin: 5px 0;
  }
  
  .company-status-icons {
    display: inline-block;
    margin-right: 8px;
  }
  
  .status-icon {
    display: inline-block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    margin-right: 4px;
    position: relative;
    top: 2px;
  }
  
  .research-done-icon {
    background-color: #4CAF50; /* Green */
    color: white;
    font-size: 10px;
    text-align: center;
    line-height: 16px;
  }
  
  .reply-sent-icon {
    background-color: #2196F3; /* Blue */
    color: white;
    font-size: 10px;
    text-align: center;
    line-height: 16px;
  }
  
  .loading-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-right: 5px;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

document.addEventListener("alpine:init", () => {
  Alpine.data("companyList", () => {
    const researchService = new CompanyResearchService();
    const emailScanningService = new EmailScanningService();
    const taskPollingService = new TaskPollingService();
    return {
      companies: [],
      loading: false,
      editingCompany: null,
      editingReply: "",
      // Local tracking for UI state
      generatingMessages: new Set(),
      researchingCompanies: new Set(),
      // Stubs for import functionality
      importingCompanies: false,
      importTaskId: null,
      importStatus: null,
      importError: null,
      sortField: "name",
      sortAsc: true,
      filterMode: "all", // "all", "with-replies", "without-replies"
      // View mode toggle functionality
      viewMode: "company_management", // "company_management" or "daily_dashboard"
      // Research company modal state
      researchCompanyModalOpen: false,
      researchingCompany: false,
      researchCompanyForm: {
        url: "",
        name: "",
      },
      researchCompanyTaskId: null,

      isUrl,

      async init() {
        console.log("Initializing companyList component");
        this.loading = true;
        try {
          // Check URL for view parameter first
          const urlParams = new URLSearchParams(window.location.search);
          const viewParam = urlParams.get('view');
          
          // Set view mode based on URL parameter
          this.viewMode = viewParam === 'daily' 
            ? "daily_dashboard" 
            : "company_management";
          
          // Check for anchor in URL
          const hash = window.location.hash;
          const companyId = hash ? decodeURIComponent(hash.substring(1)) : null;
          
          // Only load company data if in company management view
          if (this.viewMode === "company_management") {
            // Always load all companies
            await this.refreshAllCompanies();
            
            // If there's an anchor, scroll to that company after loading
            if (companyId) {
              setTimeout(() => {
                const element = document.getElementById(encodeURIComponent(companyId));
                if (element) {
                  element.scrollIntoView({ behavior: 'smooth' });
                }
              }, 100);
            }
          }
        } catch (err) {
          console.error("Failed to load companies:", err);
          this.showError("Failed to load company data");
        } finally {
          this.loading = false;
        }
      },

      // View mode toggle methods
      toggleViewMode() {
        this.viewMode =
          this.viewMode === "company_management"
            ? "daily_dashboard"
            : "company_management";
        // Update URL without reloading
        const url = new URL(window.location);
        url.searchParams.delete('company');
        url.searchParams.delete('message');
        if (this.viewMode === "daily_dashboard") {
          url.searchParams.set('view', 'daily');
        } else {
          url.searchParams.delete('view');
        }
        window.history.replaceState({}, '', url);
      },

      isCompanyManagementView() {
        return this.viewMode === "company_management";
      },

      isDailyDashboardView() {
        return this.viewMode === "daily_dashboard";
      },

      // Navigation methods
      navigateToCompany(companyId) {
        // Update URL with anchor
        const url = new URL(window.location);
        url.hash = encodeURIComponent(companyId);
        url.searchParams.delete('message');
        window.history.pushState({}, '', url);
        
        // Scroll to the company anchor
        const element = document.getElementById(encodeURIComponent(companyId));
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      },

      navigateToMessage(messageId) {
        // Update URL
        const url = new URL(window.location);
        url.searchParams.set('message', messageId);
        url.searchParams.delete('company');
        window.history.pushState({}, '', url);
        
        // Load message and associated company
        this.loadMessageAndCompany(messageId);
      },

      async loadCompany(companyId) {
        this.loading = true;
        try {
          const response = await fetch(`/api/companies/${encodeURIComponent(companyId)}`);
          if (!response.ok) {
            throw new Error(`Failed to load company: ${response.status}`);
          }
          
          const company = await response.json();
          // Get associated messages
          const messagesResponse = await fetch(`/api/messages`);
          if (messagesResponse.ok) {
            const allMessages = await messagesResponse.json();
            company.associated_messages = allMessages.filter(msg => msg.company_id === companyId);
          } else {
            company.associated_messages = [];
          }
          
          this.companies = [company];
        } catch (err) {
          console.error("Failed to load company:", err);
          this.showError("Failed to load company data");
        } finally {
          this.loading = false;
        }
      },

      async loadMessageAndCompany(messageId) {
        this.loading = true;
        try {
          // Get message details
          const messagesResponse = await fetch(`/api/messages`);
          if (!messagesResponse.ok) {
            throw new Error(`Failed to load messages: ${messagesResponse.status}`);
          }
          
          const allMessages = await messagesResponse.json();
          const message = allMessages.find(msg => msg.message_id === messageId);
          
          if (!message) {
            throw new Error("Message not found");
          }
          
          // Get associated company
          const companyResponse = await fetch(`/api/companies/${encodeURIComponent(message.company_id)}`);
          if (!companyResponse.ok) {
            throw new Error(`Failed to load company: ${companyResponse.status}`);
          }
          
          const company = await companyResponse.json();
          company.associated_messages = allMessages.filter(msg => msg.company_id === message.company_id);
          
          this.companies = [company];
          this.editingCompany = company;
          this.editingReply = company.reply_message || "";
          
          // Show edit modal for the message
          setTimeout(() => {
            document.getElementById("editModal").showModal();
          }, 100);
        } catch (err) {
          console.error("Failed to load message and company:", err);
          this.showError("Failed to load message and company data");
        } finally {
          this.loading = false;
        }
      },

      showError,
      showSuccess,

      async generateReply(company, updateModal = false) {
        try {
          // Check if company has a recruiter message
          if (
            !company.recruiter_message ||
            !company.recruiter_message.message
          ) {
            this.showError("No recruiter message to reply to");
            return;
          }

          // Add to local tracking for immediate UI update
          this.generatingMessages.add(company.name);
          // Also add to service for polling
          taskPollingService.addGeneratingMessage(company);

          const response = await fetch(
            `/api/messages/${company.recruiter_message?.message_id}/reply`,
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
          company.message_task_id = data.task_id;
          company.message_status = data.status;

          // Start polling for updates
          await this.pollMessageStatus(company);
          
          // After polling completes, get the fresh company data
          await this.fetchAndUpdateCompany(company.company_id);
          
          // Update editing modal if it's open for this company
          if (updateModal && this.editingCompany && this.editingCompany.company_id === company.company_id) {
            const updatedCompany = this.companies.find(
              (c) => c.company_id === company.company_id
            );
            if (updatedCompany) {
              this.editingReply = updatedCompany.reply_message || "";
            }
          }
          
          this.showSuccess("Reply generated successfully!");
        } catch (err) {
          console.error("Failed to generate reply:", err);
          this.showError(
            err.message || "Failed to generate reply. Please try again."
          );
        } finally {
          this.generatingMessages.delete(company.name);
          taskPollingService.removeGeneratingMessage(company);
        }
      },

      editReply(company) {
        console.log("editReply called with company:", company);
        this.editingCompany = company;
        this.editingReply = company.reply_message;
        document.getElementById("editModal").showModal();
      },

      cancelEdit() {
        console.log("cancelEdit called, clearing editingCompany");
        this.editingCompany = null;
        this.editingReply = "";
        document.getElementById("editModal").close();
        
        // Update URL to remove message parameter
        const url = new URL(window.location);
        url.searchParams.delete('message');
        window.history.replaceState({}, '', url);
      },

      async saveReply() {
        if (this.editingCompany) {
          try {
            const response = await fetch(
              `/api/messages/${this.editingCompany.recruiter_message?.message_id}/reply`,
              {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({ message: this.editingReply }),
              }
            );

            if (!response.ok) {
              const error = await response.json();
              throw new Error(
                error.error || `Failed to save reply: ${response.status}`
            );
            }

            const data = await response.json();
            // Update the local company object
            Object.assign(this.editingCompany, data);

            // Also update the companies array with fresh data
            await this.fetchAndUpdateCompany(this.editingCompany.company_id);

            this.cancelEdit();
          } catch (err) {
            console.error("Failed to save reply:", err);
            this.showError(
              err.message || "Failed to save reply. Please try again."
            );
          }
        }
      },

      async sendAndArchive(company) {
        if (!company || !company.reply_message) {
          this.showError("No reply message to send");
          return;
        }

        try {
          // First save any edits to the reply
          if (
            this.editingCompany &&
            this.editingReply !== company.reply_message
          ) {
            company.reply_message = this.editingReply;
            await this.saveReply();
          }

          // Send the reply and archive
          const response = await fetch(
            `/api/companies/${company.company_id}/send_and_archive`,
            {
              method: "POST",
            }
          );

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to send and archive: ${response.status}`
            );
          }

          const data = await response.json();

          // Fetch fresh company data instead of just updating properties
          await this.fetchAndUpdateCompany(company.company_id);

          this.showSuccess("Reply sent and message archived");
          this.cancelEdit();
        } catch (err) {
          console.error("Failed to send and archive:", err);
          this.showError(
            err.message || "Failed to send and archive. Please try again."
          );
        }
      },

      async research(company) {
        try {
          this.researchingCompanies.add(company.name);
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
          
          await this.fetchAndUpdateCompany(company.company_id);
          this.showSuccess("Company research completed!");
        } catch (err) {
          console.error("Failed to research company:", err);
          this.showError(
            err.message || "Failed to start research. Please try again."
          );
        } finally {
          this.researchingCompanies.delete(company.name);
          taskPollingService.removeResearching(company);
        }
      },

      async pollResearchStatus(company) {
        return await taskPollingService.pollResearchStatus(company);
      },
      getResearchStatusText: (company) =>
        taskPollingService.getResearchStatusText(company),
      getResearchStatusClass: (company) =>
        taskPollingService.getResearchStatusClass(company),
      isResearching(company) {
        if (!company) return false;
        return this.researchingCompanies.has(company.name);
      },
      async pollMessageStatus(company) {
        return await taskPollingService.pollMessageStatus(company);
      },
      getMessageStatusText: (company) =>
        taskPollingService.getMessageStatusText(company),
      isGeneratingMessage(company) {
        if (this.loading) return false;
        if (!company) return false;
        return this.generatingMessages.has(company.name);
      },

      async pollTaskStatus(company, taskType) {
        const isMessage = taskType === "message";
        const isImportingCompanies = taskType === "import_companies";
        const trackingSet = isMessage
          ? this.generatingMessages
          : isImportingCompanies
          ? new Set(["import_companies"]) // Single-item set for import task
          : this.researchingCompanies;
        const taskIdField = isMessage ? "message_task_id" : "research_task_id";
        const statusField = isMessage ? "message_status" : "research_status";
        const errorField = isMessage ? "message_error" : "research_error";

        const taskId = company
          ? company[taskIdField]
          : isImportingCompanies
          ? this.importTaskId
          : null;
        const trackingKey = company
          ? company.name
          : isImportingCompanies
          ? "import_companies"
          : "";

        console.log(`Starting poll for ${taskType}`, {
          companyName: company?.name,
          taskId,
        });

        // Initialize importStatus if needed before polling starts
        if (
          isImportingCompanies &&
          (!this.importStatus || typeof this.importStatus !== "object")
        ) {
          this.importStatus = {
            percent_complete: 0,
            current_company: "",
            processed: 0,
            total_found: 0,
            created: 0,
            updated: 0,
            skipped: 0,
            errors: 0,
            status: "pending",
          };
        }

        while (trackingSet.has(trackingKey)) {
          try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const task = await response.json();

            console.log(`Poll response for ${trackingKey}:`, task);

            // Update the status based on task type
            if (company) {
              company[statusField] = task.status;
            } else if (isImportingCompanies) {
              console.log("Poll response for import task:", task);
              console.log(
                "Current importStatus before update:",
                JSON.stringify(this.importStatus)
              );

              this.importStatus = task.status;

              // Update the progress information if available in the task result
              if (task.result) {
                console.log(
                  "Raw task result received:",
                  JSON.stringify(task.result)
                );

                // Save current values to preserve them if they're not in the new result
                const currentCreated =
                  this.importStatus && this.importStatus.created
                    ? this.importStatus.created
                    : 0;
                const currentUpdated =
                  this.importStatus && this.importStatus.updated
                    ? this.importStatus.updated
                    : 0;
                const currentSkipped =
                  this.importStatus && this.importStatus.skipped
                    ? this.importStatus.skipped
                    : 0;
                const currentErrors =
                  this.importStatus && this.importStatus.errors
                    ? this.importStatus.errors
                    : 0;

                this.importStatus = {
                  ...this.importStatus,
                  ...task.result,
                  current_company:
                    task.result.current_company ||
                    (this.importStatus && this.importStatus.current_company
                      ? this.importStatus.current_company
                      : ""),
                  percent_complete:
                    task.result.total_found > 0
                      ? (task.result.processed / task.result.total_found) * 100
                      : 0,
                  // Use task.result values if present, otherwise keep current values
                  created:
                    task.result.created !== undefined
                      ? task.result.created
                      : currentCreated,
                  updated:
                    task.result.updated !== undefined
                      ? task.result.updated
                      : currentUpdated,
                  skipped:
                    task.result.skipped !== undefined
                      ? task.result.skipped
                      : currentSkipped,
                  errors:
                    task.result.errors !== undefined
                      ? task.result.errors
                      : currentErrors,
                };

                console.log(
                  "Updated importStatus after merge:",
                  JSON.stringify(this.importStatus)
                );

                // Log completed import results for debugging
                if (task.status === "completed") {
                  console.log(
                    "Import completed with results:",
                    JSON.stringify(this.importStatus)
                  );
                }
              } else {
                console.warn("No result data in the task:", task);
              }
            }

            if (task.status === "completed" || task.status === "failed") {
              // For both completion and failure, fetch fresh data

              if (task.status === "failed") {
                console.log(`Task failed for ${trackingKey}:`, task.error);
                if (company) {
                  company[errorField] = task.error;
                } else if (isImportingCompanies) {
                  this.importError = task.error;
                  this.importingCompanies = false;
                }
              }

              if (company) {
                // Get fresh data for this company
                await this.fetchAndUpdateCompany(company.company_id);
              } else {
                // For import tasks, update entire companies list
                await this.refreshAllCompanies();
                if (isImportingCompanies) {
                  this.importingCompanies = false;

                  // Show result message for import
                  if (task.status === "completed") {
                    console.log("Import task completed. Full task data:", task);

                    // Even if there's no result in the final task response,
                    // we may have collected statistics during the polling process
                    if (!task.result && this.importStatus) {
                      console.log(
                        "No result in completed task, using collected importStatus:",
                        this.importStatus
                      );

                      // Show success message with the stats we've collected
                      const created = this.importStatus.created || 0;
                      const updated = this.importStatus.updated || 0;
                      const skipped = this.importStatus.skipped || 0;
                      const errors = this.importStatus.errors || 0;

                      const msg = `Import completed! Created: ${created}, Updated: ${updated}, Skipped: ${skipped}, Errors: ${errors}`;
                      this.showSuccess(msg);

                      // Reset importStatus since we're done and only using alert
                      this.importStatus = null;
                    } else if (task.result) {
                      const result = task.result;
                      console.log("Import result data is present:", result);

                      const msg = `Import completed! Created: ${
                        result.created || 0
                      }, Updated: ${result.updated || 0}, Skipped: ${
                        result.skipped || 0
                      }, Errors: ${result.errors || 0}`;
                      this.showSuccess(msg);

                      // Reset importStatus since we're done and only using alert
                      this.importStatus = null;
                    } else {
                      console.error(
                        "Import task completed but no result data available!"
                      );
                      this.showError(
                        "Import completed but no statistics available"
                      );

                      // Reset importStatus
                      this.importStatus = null;
                    }
                  }
                }
              }

              trackingSet.delete(trackingKey);
              break;
            }

            await new Promise((resolve) => setTimeout(resolve, 1000));
          } catch (err) {
            console.error(`Failed to poll ${taskType} status:`, err);
            if (company) {
              // Do nothing, keep polling
            } else if (isImportingCompanies) {
              this.importError = "Failed to check task status";
              this.importingCompanies = false;
            }
            trackingSet.delete(trackingKey);
            break;
          }
        }
      },

      async scanEmails(maxMessages = 10) {
        try {
          // Use the shared email scanning service
          await emailScanningService.scanRecruiterEmails(false); // Default to no research
          await this.pollEmailScanStatus();
        } catch (err) {
          console.error("Failed to scan recruiter emails:", err);
          this.showError(
            err.message || "Failed to scan emails. Please try again."
          );
        }
      },

      // Poll for email scan task status
      async pollEmailScanStatus() {
        const result = await emailScanningService.pollEmailScanStatus();

        if (result?.status === "completed") {
          // Refresh companies after successful scan
          await this.refreshAllCompanies();
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

      // Alias for scanEmails to match HTML expectations
      async scanRecruiterEmails() {
        return this.scanEmails();
      },

      // Stub function for importing companies from spreadsheet
      importCompaniesFromSpreadsheet() {
        // This is just a stub to fix the error
        console.log("Import companies stub called");
      },

      async importCompaniesFromSpreadsheet() {
        if (this.importingCompanies) {
          return; // Already importing
        }

        this.closeImportCompaniesModal();
        this.importingCompanies = true;
        this.importError = null;
        this.importStatus = {
          percent_complete: 0,
          current_company: "",
          processed: 0,
          total_found: 0,
          created: 0,
          updated: 0,
          skipped: 0,
          errors: 0,
          status: "pending",
        };

        console.log(
          "Starting import with initial importStatus:",
          JSON.stringify(this.importStatus)
        );

        try {
          const response = await fetch("/api/import_companies", {
            method: "POST",
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || response.statusText);
          }

          const data = await response.json();
          this.importTaskId = data.task_id;
          console.log("Import task created with ID:", this.importTaskId);

          // Start polling for task status
          this.pollTaskStatus(null, "import_companies");
        } catch (error) {
          console.error("Error starting import:", error);
          this.importingCompanies = false;
          this.importError = error.message;
          this.showError(`Failed to start import: ${error.message}`);
        }
      },

      // Restored methods from git history (removed in commit 54d57a7)

      get filteredCompanies() {
        const filtered = this.companies.filter((company) => {
          switch (this.filterMode) {
            case "reply-sent":
              return company.sent_at;
            case "reply-not-sent":
              return !company.sent_at;
            case "researched":
              return company.research_completed_at;
            case "not-researched":
              return !company.research_completed_at;
            default:
              return true;
          }
        });
        return filtered;
      },

      get sortedAndFilteredCompanies() {
        return [...this.filteredCompanies].sort((a, b) => {
          const aVal =
            this.sortField === "updated_at"
              ? new Date(a.updated_at).getTime()
              : a[this.sortField];
          const bVal =
            this.sortField === "updated_at"
              ? new Date(b.updated_at).getTime()
              : b[this.sortField];

          const comparison = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
          return this.sortAsc ? comparison : -comparison;
        });
      },

      toggleSort(field) {
        if (this.sortField === field) {
          this.sortAsc = !this.sortAsc;
        } else {
          this.sortField = field;
          this.sortAsc = true;
        }
      },

      formatRecruiterMessageDate,

      // New method to fetch and update a single company
      async fetchAndUpdateCompany(companyId) {
        try {
          const response = await fetch(
            `/api/companies/${encodeURIComponent(companyId)}`
          );
          if (!response.ok) {
            console.error(`Failed to fetch company data for ${companyId}`);
            return;
          }

          const updatedCompany = await response.json();
          console.log(`Fetched fresh data for ${companyId}:`, updatedCompany);

          // Find and replace the company in our array
          const index = this.companies.findIndex(
            (c) => c.company_id === companyId
          );
          if (index !== -1) {
            // Make sure to preserve details object structure
            this.companies[index] = {
              ...updatedCompany,
              details: updatedCompany.details || {},
            };

            // If this is also the current editing company, update that reference
            if (
              this.editingCompany &&
              this.editingCompany.company_id === companyId
            ) {
              Object.assign(this.editingCompany, updatedCompany);
              this.editingReply = updatedCompany.reply_message;
            }
          }
        } catch (err) {
          console.error("Error fetching individual company:", err);
        }
      },

      // New method to refresh all companies
      async refreshAllCompanies() {
        console.log("Refreshing all companies");
        try {
          const response = await fetch("/api/companies");
          const data = await response.json();
          console.log("Got companies json response");
          this.companies = data.map((company) => ({
            ...company,
            details: company.details || {},
          }));
          return data;
        } catch (err) {
          console.error("Failed to refresh companies:", err);
          return [];
        }
      },

      formatResearchErrors(company) {
        if (!company || !company.research_errors) return "";

        // If it's already a formatted string, just return it
        if (typeof company.research_errors === "string") {
          return company.research_errors;
        }

        // If it's an array of objects, try to format it
        if (Array.isArray(company.research_errors)) {
          return company.research_errors
            .map((err) => {
              if (typeof err === "string") return err;
              if (err && err.step && err.error)
                return `${err.step}: ${err.error}`;
              return JSON.stringify(err);
            })
            .join("; ");
        }

        // Fallback for unknown formats
        return JSON.stringify(company.research_errors);
      },

      async ignoreAndArchive(company) {
        if (!company) {
          this.showError("No company selected");
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
          // Get the message ID from the company's recruiter message
          const messageId = company.recruiter_message?.message_id;

          if (!messageId) {
            this.showError("No message ID found for this company");
            return;
          }

          // Call the new message-centric archive endpoint
          const response = await fetch(`/api/messages/${messageId}/archive`, {
            method: "POST",
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to archive message: ${response.status}`
            );
          }

          const data = await response.json();

          // Fetch fresh company data
          await this.fetchAndUpdateCompany(company.company_id);

          this.showSuccess("Message archived without reply");
          this.cancelEdit();
        } catch (err) {
          console.error("Failed to archive message:", err);
          this.showError(
            err.message || "Failed to archive message. Please try again."
          );
        }
      },

      togglePromising(company, value) {
        if (!company) return;

        // If clicking the same value that's already set, clear it
        if (company.promising === value) {
          value = null;
        }

        company.promising = value;

        // Save to backend
        fetch(
          `/api/companies/${encodeURIComponent(company.company_id)}/details`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ promising: value }),
          }
        )
          .then((response) => {
            if (!response.ok) {
              // Revert the local change if the server update failed
              company.promising = null;
            }
          })
          .catch((err) => {
            console.error("Failed to update promising status:", err);
            // Revert the local change if the server update failed
            company.promising = null;
          });
      },

      showResearchCompanyModal() {
        console.log("showResearchCompanyModal called");
        document.getElementById("research-company-modal").showModal();
        this.researchCompanyForm = {
          url: "",
          name: "",
        };
        console.log("Modal form reset");
      },

      closeResearchCompanyModal() {
        document.getElementById("research-company-modal").close();
      },

      showImportCompaniesModal() {
        // Show the import companies modal dialog
        document.getElementById("import-companies-modal").showModal();
      },

      closeImportCompaniesModal() {
        // Close the import companies modal dialog
        document.getElementById("import-companies-modal").close();
      },

      confirmImportCompanies() {
        // Close the modal and start the import
        this.closeImportCompaniesModal();
        this.importCompaniesFromSpreadsheet();
      },

      async submitResearchCompany() {
        try {
          console.log(
            "submitResearchCompany called with form data:",
            this.researchCompanyForm
          );
          // Validate form
          if (!this.researchCompanyForm.url && !this.researchCompanyForm.name) {
            this.showError("Please provide either a company URL or name");
            return;
          }

          this.researchingCompany = true;
          console.log("Set researchingCompany to true");

          const data = await researchService.submitResearch(
            this.researchCompanyForm
          );
          console.log("API success response:", data);
          this.researchCompanyTaskId = data.task_id;

          // Close modal and show success message
          this.closeResearchCompanyModal();
          this.showSuccess(
            "Company research started. This may take a few minutes."
          );

          // Poll for task completion
          console.log("Starting to poll task:", this.researchCompanyTaskId);
          this.pollResearchCompanyTask();
        } catch (err) {
          console.error("Failed to research company:", err);
          this.showError(
            err.message || "Failed to start research. Please try again."
          );
        } finally {
          this.researchingCompany = researchService.researchingCompany;
          console.log("Set researchingCompany back to false");
        }
      },

      async pollResearchCompanyTask() {
        if (!this.researchCompanyTaskId) return;

        try {
          const data = await researchService.pollResearchTask(
            this.researchCompanyTaskId
          );

          if (data.status === "completed") {
            this.showSuccess("Company research completed!");
            this.researchCompanyTaskId = null;
            await this.refreshAllCompanies();
          } else if (data.status === "failed") {
            this.showError(`Research failed: ${data.error || "Unknown error"}`);
            this.researchCompanyTaskId = null;
          } else {
            // Task still running, check again in 5 seconds
            setTimeout(() => this.pollResearchCompanyTask(), 5000);
          }
        } catch (err) {
          console.error("Error polling research task:", err);
          this.showError(
            "Failed to check research status. Please refresh the page."
          );
          this.researchCompanyTaskId = null;
        }
      },
    };
  });
});
