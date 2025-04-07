import { CompanyResearchService } from "./company-research.js";

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
`;
document.head.appendChild(style);

document.addEventListener("alpine:init", () => {
  Alpine.data("companyList", () => {
    const researchService = new CompanyResearchService();
    return {
      companies: [],
      loading: false,
      editingCompany: null,
      editingReply: "",
      researchingCompanies: new Set(),
      generatingMessages: new Set(),
      scanningEmails: false,
      emailScanTaskId: null,
      emailScanStatus: null,
      emailScanError: null,
      // Stubs for import functionality
      importingCompanies: false,
      importTaskId: null,
      importStatus: null,
      importError: null,
      sortField: "name",
      sortAsc: true,
      filterMode: "all", // "all", "with-replies", "without-replies"
      // Research company modal state
      researchCompanyModalOpen: false,
      researchingCompany: false,
      researchCompanyForm: {
        url: "",
        name: "",
      },
      researchCompanyTaskId: null,

      isUrl(value) {
        return typeof value === "string" && value.startsWith("http");
      },

      async init() {
        console.log("Initializing companyList component");
        this.loading = true;
        try {
          await this.refreshAllCompanies();
        } catch (err) {
          console.error("Failed to load companies:", err);
        } finally {
          this.loading = false;
        }
      },

      showError(message) {
        alert(message); // We can make this fancier later with a toast or custom modal
      },

      showSuccess(message) {
        alert(message); // Simple success notification, can be improved later
      },

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

          this.generatingMessages.add(company.name);
          const response = await fetch(
            `/api/companies/${company.company_id}/reply_message`,
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
          if (updateModal && this.editingCompany) {
            const updatedCompany = this.companies.find(
              (c) => c.name === company.name
            );
            if (updatedCompany) {
              this.editingReply = updatedCompany.reply_message;
            }
          }
        } catch (err) {
          console.error("Failed to generate reply:", err);
          this.showError(
            err.message || "Failed to generate reply. Please try again."
          );
        } finally {
          this.generatingMessages.delete(company.name);
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
      },

      async saveReply() {
        if (this.editingCompany) {
          try {
            const response = await fetch(
              `/api/companies/${this.editingCompany.company_id}/reply_message`,
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
          this.showError(
            err.message || "Failed to start research. Please try again."
          );
        } finally {
          this.researchingCompanies.delete(company.name);
        }
      },

      async pollResearchStatus(company) {
        return this.pollTaskStatus(company, "research");
      },

      getResearchStatusText(company) {
        return this.getTaskStatusText(company, "research");
      },

      getResearchStatusClass(company) {
        return {
          "status-pending": company.research_status === "pending",
          "status-running": company.research_status === "running",
          "status-completed": company.research_status === "completed",
          "status-failed":
            company.research_status === "failed" || company.research_error,
        };
      },

      isResearching(company) {
        return this.researchingCompanies.has(company.name);
      },

      async pollMessageStatus(company) {
        return this.pollTaskStatus(company, "message");
      },

      getMessageStatusText(company) {
        return this.getTaskStatusText(company, "message");
      },

      isGeneratingMessage(company) {
        if (this.loading) return false;
        if (!company) return false;
        return this.generatingMessages.has(company.name);
      },

      async pollTaskStatus(company, taskType) {
        const isMessage = taskType === "message";
        const isScanningEmails = taskType === "scan_emails";
        const isImportingCompanies = taskType === "import_companies";
        const trackingSet = isMessage
          ? this.generatingMessages
          : isScanningEmails
          ? new Set(["scan_emails"]) // Single-item set for email scanning task
          : isImportingCompanies
          ? new Set(["import_companies"]) // Single-item set for import task
          : this.researchingCompanies;
        const taskIdField = isMessage ? "message_task_id" : "research_task_id";
        const statusField = isMessage ? "message_status" : "research_status";
        const errorField = isMessage ? "message_error" : "research_error";

        const taskId = company
          ? company[taskIdField]
          : isScanningEmails
          ? this.emailScanTaskId
          : isImportingCompanies
          ? this.importTaskId
          : null;
        const trackingKey = company
          ? company.name
          : isScanningEmails
          ? "scan_emails"
          : isImportingCompanies
          ? "import_companies"
          : "";

        console.log(`Starting poll for ${taskType}`, {
          companyName: company?.name,
          taskId,
        });

        while (trackingSet.has(trackingKey)) {
          try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const task = await response.json();

            console.log(`Poll response for ${trackingKey}:`, task);

            // Update the status based on task type
            if (company) {
              company[statusField] = task.status;
            } else if (isScanningEmails) {
              this.emailScanStatus = task.status;
            } else if (isImportingCompanies) {
              this.importStatus = task.status;
            }

            if (task.status === "completed" || task.status === "failed") {
              // For both completion and failure, fetch fresh data

              if (task.status === "failed") {
                console.log(`Task failed for ${trackingKey}:`, task.error);
                if (company) {
                  company[errorField] = task.error;
                } else if (isScanningEmails) {
                  this.emailScanError = task.error;
                  this.scanningEmails = false;
                } else if (isImportingCompanies) {
                  this.importError = task.error;
                  this.importingCompanies = false;
                }
              }

              if (company) {
                // Get fresh data for this company
                await this.fetchAndUpdateCompany(company.company_id);
              } else {
                // For email scanning or import tasks, update entire companies list
                await this.refreshAllCompanies();
                if (isScanningEmails) {
                  this.scanningEmails = false;
                } else if (isImportingCompanies) {
                  this.importingCompanies = false;

                  // Show result message for import
                  if (task.status === "completed" && task.result) {
                    const result = task.result;
                    const msg = `Import completed! Created: ${result.created}, Updated: ${result.updated}, Skipped: ${result.skipped}, Errors: ${result.errors}`;
                    this.showSuccess(msg);
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
            } else if (isScanningEmails) {
              this.emailScanError = "Failed to check task status";
              this.scanningEmails = false;
            } else if (isImportingCompanies) {
              this.importError = "Failed to check task status";
              this.importingCompanies = false;
            }
            trackingSet.delete(trackingKey);
            break;
          }
        }
      },

      async scanRecruiterEmails(maxMessages) {
        if (this.scanningEmails) return;

        try {
          this.scanningEmails = true;
          this.emailScanError = null;
          // Get the research checkbox value
          const doResearch = document.getElementById("doResearch").checked;

          const response = await fetch("/api/scan_recruiter_emails", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              max_messages: maxMessages,
              do_research: doResearch,
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

          await this.pollTaskStatus(null, "scan_emails");
        } catch (err) {
          console.error("Failed to scan recruiter emails:", err);
          this.showError(
            err.message || "Failed to scan emails. Please try again."
          );
          this.emailScanError = err.message;
        } finally {
          this.scanningEmails = false;
        }
      },

      getEmailScanStatusText() {
        if (this.emailScanError) {
          return `Failed: ${this.emailScanError}`;
        }
        switch (this.emailScanStatus) {
          case "pending":
            return "Starting email scan...";
          case "running":
            return "Scanning recruiter emails...";
          case "completed":
            return "Email scan complete";
          case "failed":
            return "Failed to scan emails";
          default:
            return "";
        }
      },

      getEmailScanStatusClass() {
        return {
          "status-pending": this.emailScanStatus === "pending",
          "status-running": this.emailScanStatus === "running",
          "status-completed": this.emailScanStatus === "completed",
          "status-failed": this.emailScanStatus === "failed",
        };
      },

      getTaskStatusText(company, taskType) {
        const isMessage = taskType === "message";
        const status = isMessage
          ? company.message_status
          : company.research_status;
        const error = isMessage
          ? company.message_error
          : company.research_error;
        const action = isMessage ? "Generation" : "Research";

        if (error) {
          return `${action} failed: ${error}`;
        }
        switch (status) {
          case "pending":
            return isMessage ? "Generating message..." : "Research pending...";
          case "running":
            return isMessage ? "Generating..." : "Researching...";
          case "completed":
            return isMessage ? "Message generated" : "Research complete";
          case "failed":
            return `${action} failed`;
          default:
            return "";
        }
      },

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

      formatRecruiterMessageDate(dateString) {
        if (!dateString) return "";

        const date = new Date(dateString);
        const now = new Date();

        // Calculate days ago
        const diffTime = Math.abs(now - date);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        // Format the date as YYYY/MM/DD
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");

        // Format the time as h:mm am/pm
        let hours = date.getHours();
        const ampm = hours >= 12 ? "pm" : "am";
        hours = hours % 12;
        hours = hours ? hours : 12; // the hour '0' should be '12'
        const minutes = String(date.getMinutes()).padStart(2, "0");

        return `${year}/${month}/${day} ${hours}:${minutes}${ampm} (${diffDays} days ago)`;
      },

      // New method to fetch and update a single company
      async fetchAndUpdateCompany(companyId) {
        try {
          const response = await fetch(`/api/companies/${companyId}`);
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
          // Call the ignore and archive endpoint
          const response = await fetch(
            `/api/companies/${company.company_id}/ignore_and_archive`,
            {
              method: "POST",
            }
          );

          if (!response.ok) {
            const error = await response.json();
            throw new Error(
              error.error || `Failed to ignore and archive: ${response.status}`
            );
          }

          const data = await response.json();

          // Fetch fresh company data
          await this.fetchAndUpdateCompany(company.company_id);

          this.showSuccess("Message archived without reply");
          this.cancelEdit();
        } catch (err) {
          console.error("Failed to ignore and archive:", err);
          this.showError(
            err.message || "Failed to ignore and archive. Please try again."
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
        fetch(`/api/companies/${company.company_id}/details`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ promising: value }),
        })
          .then((response) => {
            if (!response.ok) {
              throw new Error("Failed to update company promising status");
            }
            return response.json();
          })
          .then((data) => {
            console.log(`Set ${company.name} promising status to:`, value);
          })
          .catch((error) => {
            console.error("Error updating company status:", error);
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

      async scanEmails(maxMessages = 10) {
        if (this.scanningEmails) {
          return; // Already scanning
        }

        // Rest of scanning code here...
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

        this.importingCompanies = true;
        this.importError = null;
        this.importStatus = "pending";

        try {
          const response = await fetch("/api/import_companies", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || response.statusText);
          }

          const data = await response.json();
          this.importTaskId = data.task_id;

          // Start polling for task status
          this.pollTaskStatus(null, "import_companies");
        } catch (error) {
          console.error("Error starting import:", error);
          this.importingCompanies = false;
          this.importError = error.message;
          this.showError(`Failed to start import: ${error.message}`);
        }
      },
    };
  });
});
