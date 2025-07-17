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

      // View mode toggle methods
      toggleViewMode() {
        this.viewMode =
          this.viewMode === "company_management"
            ? "daily_dashboard"
            : "company_management";
      },

      isCompanyManagementView() {
        return this.viewMode === "company_management";
      },

      isDailyDashboardView() {
        return this.viewMode === "daily_dashboard";
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
            } else if (isScanningEmails) {
              this.emailScanStatus = task.status;
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
    };
  });
});
