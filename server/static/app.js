document.addEventListener("alpine:init", () => {
  Alpine.data("companyList", () => ({
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
    sortField: "name",
    sortAsc: true,
    filterMode: "all", // "all", "with-replies", "without-replies"

    isUrl(value) {
      return typeof value === "string" && value.startsWith("http");
    },

    async init() {
      this.loading = true;
      try {
        const response = await fetch("/api/companies");
        const data = await response.json();
        // Make the entire companies array and its contents reactive from the start
        this.companies = data.map((company) => ({
          ...company,
          details: company.details || {},
        }));
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
        this.generatingMessages.add(company.name);
        const response = await fetch(`/api/${company.name}/reply_message`, {
          method: "POST",
        });

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
      this.editingCompany = company;
      this.editingReply = company.reply_message;
      document.getElementById("editModal").showModal();
    },

    cancelEdit() {
      this.editingCompany = null;
      this.editingReply = "";
      document.getElementById("editModal").close();
    },

    async saveReply() {
      if (this.editingCompany) {
        try {
          const response = await fetch(
            `/api/${this.editingCompany.name}/reply_message`,
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
          Object.assign(this.editingCompany, data);
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
        if (this.editingCompany && this.editingReply !== company.reply_message) {
          company.reply_message = this.editingReply;
          await this.saveReply();
        }

        // Send the reply and archive
        const response = await fetch(`/api/${company.name}/send_and_archive`, {
          method: "POST",
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(
            error.error || `Failed to send and archive: ${response.status}`
          );
        }

        const data = await response.json();
        
        // Update the company data
        const updatedCompany = this.companies.find(c => c.name === company.name);
        if (updatedCompany) {
          updatedCompany.sent_at = data.sent_at;
          updatedCompany.archived = true;
        }
        
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
        const response = await fetch(`/api/${company.name}/research`, {
          method: "POST",
        });

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
      return this.generatingMessages.has(company.name);
    },

    async pollTaskStatus(company, taskType) {
      const isMessage = taskType === "message";
      const isScanningEmails = taskType === "scan_emails";
      const trackingSet = isMessage
        ? this.generatingMessages
        : isScanningEmails
        ? new Set(["scan_emails"]) // Single-item set for email scanning task
        : this.researchingCompanies;
      const taskIdField = isMessage ? "message_task_id" : "research_task_id";
      const statusField = isMessage ? "message_status" : "research_status";
      const errorField = isMessage ? "message_error" : "research_error";

      const taskId = company ? company[taskIdField] : this.emailScanTaskId;
      const trackingKey = company ? company.name : "scan_emails";

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
          } else {
            this.emailScanStatus = task.status;
          }

          if (task.status === "completed") {
            // Fetch fresh company data from the server
            const companyResponse = await fetch("/api/companies");
            const companies = await companyResponse.json();

            if (company) {
              const updatedCompany = companies.find(
                (c) => c.name === company.name
              );
              if (updatedCompany) {
                console.log(`Updating company with fresh data:`, {
                  before: company,
                  after: updatedCompany,
                });
                
                // The research_completed_at is now set on the server via events
                
                // Find and replace the company in our array
                const index = this.companies.findIndex(
                  (c) => c.name === company.name
                );
                if (index !== -1) {
                  this.companies[index] = updatedCompany;
                }
              }
            } else {
              // For email scanning tasks, update entire companies list
              this.companies = companies.map((company) => ({
                ...company,
                details: company.details || {},
              }));
              this.scanningEmails = false;
            }
            trackingSet.delete(trackingKey);
            break;
          } else if (task.status === "failed") {
            console.log(`Task failed for ${trackingKey}:`, task.error);
            if (company) {
              company[errorField] = task.error;
            } else {
              this.emailScanError = task.error;
              this.scanningEmails = false;
            }
            trackingSet.delete(trackingKey);
            break;
          }

          await new Promise((resolve) => setTimeout(resolve, 1000));
        } catch (err) {
          console.error(`Failed to poll ${taskType} status:`, err);
          if (!company) {
            this.emailScanError = "Failed to check task status";
            this.scanningEmails = false;
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
            do_research: doResearch 
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
      const error = isMessage ? company.message_error : company.research_error;
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
          case "with-replies":
            return company.reply_message;
          case "without-replies":
            return !company.reply_message;
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
  }));
});
