import { CompaniesService } from "./companies-service.js";
import { CompanyResearchService } from "./company-research.js";
import {
  aliasOverlap,
  filterCompanies,
  findDuplicateCandidates,
  normalizeCompanies,
  sortCompanies,
  formatResearchErrors as utilFormatResearchErrors,
} from "./company-utils.js";
import { EmailScanningService } from "./email-scanning.js";
import { TaskPollingService } from "./task-polling.js";
import {
  confirmDialogs,
  errorLogger,
  formatRecruiterMessageDate,
  isUrl,
  modalUtils,
  showError,
  showSuccess,
} from "./ui-utils.js";
import {
  buildHashForCompany,
  parseViewFromUrl,
  setIncludeAllParam,
  urlUtils,
} from "./url-utils.js";

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
  // Listen for navigation events from other components
  document.addEventListener("navigate-to-company", (event) => {
    const companyId = event.detail;
    // Access the companyList component through the DOM
    const companyListElement = document.querySelector('[x-data="companyList"]');
    if (companyListElement && companyListElement._x_dataStack) {
      const companyList = companyListElement._x_dataStack[0];
      companyList.navigateToCompany(companyId);
    }
  });

  // Listen for edit reply events from daily dashboard
  document.addEventListener("edit-reply", (event) => {
    const message = event.detail;
    // Access the companyList component through the DOM
    const companyListElement = document.querySelector('[x-data="companyList"]');
    if (companyListElement && companyListElement._x_dataStack) {
      const companyList = companyListElement._x_dataStack[0];
      // Convert message to company format for the existing editReply method
      const company = {
        company_id: message.company_id,
        name: message.company_name,
        reply_message: message.reply_message,
        recruiter_message: message,
      };
      companyList.editReply(company);
    }
  });

  Alpine.data("companyList", () => {
    const researchService = new CompanyResearchService();
    const companiesService = new CompaniesService();
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
      sendingMessages: new Set(),
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

      // Duplicate detection modal state
      duplicateModalOpen: false,
      searchingDuplicates: false,
      duplicateSearchResults: [],
      selectedDuplicateCompany: null,
      duplicateSearchQuery: "",
      currentCompanyForDuplicate: null,
      potentialDuplicatesMap: {},
      dismissedDuplicatePrompts: new Set(),

      isUrl,

      async init() {
        console.log("Initializing companyList component");
        this.loading = true;
        try {
          // Check URL for view parameter first
          const viewMode = parseViewFromUrl(window.location.search);
          const urlParams = new URLSearchParams(window.location.search);
          const includeAllParam = urlParams.get("include_all") === "true";

          // Set view mode based on URL parameter
          this.viewMode = viewMode;

          // Track show archived state
          this.showArchived = includeAllParam;

          // Check for anchor in URL
          const hash = window.location.hash;
          const companyId = hash ? decodeURIComponent(hash.substring(1)) : null;

          // Only load company data if in company management view
          if (this.viewMode === "company_management") {
            await this.refreshAllCompanies(this.showArchived);

            // If there's an anchor, scroll to that company after loading
            if (companyId) {
              setTimeout(() => {
                const element = document.getElementById(
                  buildHashForCompany(companyId)
                );
                if (element) {
                  element.scrollIntoView({ behavior: "smooth" });
                }
              }, 100);
            }
          }
        } catch (err) {
          errorLogger.logFailedTo("load companies", err);
          this.showError("Failed to load company data");
        } finally {
          this.loading = false;
        }
      },

      // Duplicate detection methods
      showDuplicateModal(company) {
        this.currentCompanyForDuplicate = company;
        modalUtils.showModal(modalUtils.modalIds.DUPLICATE);
        this.duplicateSearchQuery = "";
        this.duplicateSearchResults = [];
        this.selectedDuplicateCompany = null;
        this.searchingDuplicates = false;
      },

      closeDuplicateModal() {
        modalUtils.closeModal(modalUtils.modalIds.DUPLICATE);
        this.currentCompanyForDuplicate = null;
        this.duplicateSearchQuery = "";
        this.duplicateSearchResults = [];
        this.selectedDuplicateCompany = null;
        this.searchingDuplicates = false;
      },

      async searchDuplicates() {
        if (!this.duplicateSearchQuery.trim() || !this.currentCompanyForDuplicate) {
          return;
        }

        this.searchingDuplicates = true;
        try {
          const companies = await companiesService.getCompanies(true);
          const matches = findDuplicateCandidates(
            companies,
            this.currentCompanyForDuplicate,
            this.duplicateSearchQuery
          );
          this.duplicateSearchResults = matches.slice(0, 10);
        } catch (err) {
          errorLogger.logFailedTo("search duplicates", err);
          this.showError("Failed to search for companies");
        } finally {
          this.searchingDuplicates = false;
        }
      },

      selectDuplicateCompany(company) {
        this.selectedDuplicateCompany = company;
      },

      async mergeCompanies() {
        if (!this.selectedDuplicateCompany || !this.currentCompanyForDuplicate) {
          this.showError("Please select a company to merge");
          return;
        }

        try {
          await companiesService.mergeCompanies(
            this.currentCompanyForDuplicate.company_id,
            this.selectedDuplicateCompany.company_id
          );

          this.showSuccess("Merge task started. This may take a few moments.");
          this.closeDuplicateModal();
          await this.refreshAllCompanies(this.showArchived);
        } catch (err) {
          errorLogger.logFailedTo("merge companies", err);
          this.showError(
            err.message || "Failed to start merge. Please try again."
          );
        }
      },

      getAliasOverlap(canonicalCompany, duplicateCompany) {
        return aliasOverlap(canonicalCompany, duplicateCompany);
      },

      // Duplicate prompts and notifications
      async checkPotentialDuplicates(company) {
        if (!company || !company.company_id) return [];
        try {
          const list = await companiesService.getPotentialDuplicates(
            company.company_id
          );
          this.potentialDuplicatesMap[company.company_id] = list || [];
          return list || [];
        } catch (err) {
          errorLogger.logFailedTo("load potential duplicates", err);
          return [];
        }
      },

      hasPotentialDuplicates(company) {
        if (!company || !company.company_id) return false;
        if (this.dismissedDuplicatePrompts.has(company.company_id)) return false;
        const list = this.potentialDuplicatesMap[company.company_id];
        return Array.isArray(list) && list.length > 0;
      },

      reviewDuplicates(company) {
        if (!company) return;
        this.showDuplicateModal(company);
      },

      dismissPotentialDuplicates(companyId) {
        if (!companyId) return;
        this.dismissedDuplicatePrompts.add(companyId);
      },

      // View mode toggle methods
      toggleViewMode() {
        this.viewMode =
          this.viewMode === "company_management"
            ? "daily_dashboard"
            : "company_management";
        // Update URL without reloading
        urlUtils.updateUrlParams(
          {
            company: null,
            message: null,
            view: this.viewMode === "daily_dashboard" ? "daily" : null,
          },
          true
        );
      },

      isCompanyManagementView() {
        return this.viewMode === "company_management";
      },

      isDailyDashboardView() {
        return this.viewMode === "daily_dashboard";
      },

      // Navigation methods
      navigateToCompany(companyId) {
        // Ensure we're in company management view
        this.viewMode = "company_management";

        // Update URL with anchor and preserve include_all parameter
        const url = urlUtils.createUrl();
        url.hash = encodeURIComponent(companyId);
        url.searchParams.delete("message");
        url.searchParams.delete("view");
        setIncludeAllParam(url, this.showArchived);
        window.history.pushState({}, "", url);

        // Ensure companies are loaded with current include_all setting
        this.refreshAllCompanies(this.showArchived).then(() => {
          // Scroll to the company anchor
          setTimeout(() => {
            const element = document.getElementById(
              encodeURIComponent(companyId)
            );
            if (element) {
              element.scrollIntoView({ behavior: "smooth" });
            }
          }, 100);
        });
      },

      navigateToMessage(messageId) {
        // Update URL
        urlUtils.updateUrlParams({ message: messageId, company: null }, false);

        // Load message and associated company
        this.loadMessageAndCompany(messageId);
      },

      async loadCompany(companyId) {
        this.loading = true;
        try {
          const company = await companiesService.loadCompany(companyId);
          this.companies = [company];
        } catch (err) {
          errorLogger.logFailedTo("load company", err);
          this.showError("Failed to load company data");
        } finally {
          this.loading = false;
        }
      },

      async loadMessageAndCompany(messageId) {
        this.loading = true;
        try {
          const { company, message } =
            await companiesService.loadMessageAndCompany(messageId);

          this.companies = [company];
          this.editingCompany = company;
          this.editingReply = company.reply_message || "";

          // Show edit modal for the message
          setTimeout(() => {
            modalUtils.showModal(modalUtils.modalIds.EDIT);
          }, 100);
        } catch (err) {
          errorLogger.logFailedTo("load message and company", err);
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

          const data = await companiesService.generateReply(
            company.recruiter_message?.message_id
          );
          company.message_task_id = data.task_id;
          company.message_status = data.status;

          // Start polling for updates
          await this.pollMessageStatus(company);

          // After polling completes, get the fresh company data
          await this.fetchAndUpdateCompany(company.company_id);

          // Update editing modal if it's open for this company
          if (
            updateModal &&
            this.editingCompany &&
            this.editingCompany.company_id === company.company_id
          ) {
            const updatedCompany = this.companies.find(
              (c) => c.company_id === company.company_id
            );
            if (updatedCompany) {
              this.editingReply = updatedCompany.reply_message || "";
            }
          }

          this.showSuccess("Reply generated successfully!");
        } catch (err) {
          errorLogger.logFailedTo("generate reply", err);
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
        modalUtils.showModal(modalUtils.modalIds.EDIT);
      },

      cancelEdit() {
        console.log("cancelEdit called, clearing editingCompany");
        this.editingCompany = null;
        this.editingReply = "";
        modalUtils.closeModal(modalUtils.modalIds.EDIT);

        // Update URL to remove message parameter
        urlUtils.removeUrlParams(["message"]);
      },

      async saveReply() {
        if (this.editingCompany) {
          try {
            const data = await companiesService.saveReply(
              this.editingCompany.recruiter_message?.message_id,
              this.editingReply
            );

            // Update the local company object
            Object.assign(this.editingCompany, data);

            // Refresh data based on current view mode
            if (this.isDailyDashboardView()) {
              // Refresh messages in daily dashboard
              const dailyDashboardElement = document.querySelector(
                '[x-data="dailyDashboard"]'
              );
              if (dailyDashboardElement && dailyDashboardElement._x_dataStack) {
                const dailyDashboard = dailyDashboardElement._x_dataStack[0];
                await dailyDashboard.loadMessages();
              }
            } else {
              // Refresh companies in company management view
              await this.fetchAndUpdateCompany(this.editingCompany.company_id);
            }

            this.cancelEdit();
          } catch (err) {
            errorLogger.logFailedTo("save reply", err);
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

        // Add to local tracking for immediate UI update - do this BEFORE any API calls
        this.sendingMessages.add(company.name);
        // Also add to service for polling
        taskPollingService.addSendingMessage(company);

        try {
          // First save any edits to the reply
          if (
            this.editingCompany &&
            this.editingReply !== company.reply_message
          ) {
            company.reply_message = this.editingReply;
            await this.saveReply();
          }

          // Check if we have a message_id to use the message-centric endpoint
          if (
            company.recruiter_message &&
            company.recruiter_message.message_id
          ) {
            // Use the message-centric endpoint via service
            await companiesService.sendAndArchive(
              company.recruiter_message.message_id
            );
          } else {
            // Fallback to company-centric endpoint for backward compatibility
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
          }

          // Fetch fresh company data instead of just updating properties
          await this.fetchAndUpdateCompany(company.company_id);

          this.showSuccess("Reply sent and message archived");
          this.cancelEdit();
        } catch (err) {
          errorLogger.logFailedTo("send and archive", err);
          this.showError(
            err.message || "Failed to send and archive. Please try again."
          );
        } finally {
          this.sendingMessages.delete(company.name);
          taskPollingService.removeSendingMessage(company);
        }
      },

      async research(company) {
        try {
          this.researchingCompanies.add(company.name);
          taskPollingService.addResearching(company);
          const data = await companiesService.research(company.company_id);
          company.research_task_id = data.task_id;
          company.research_status = data.status;

          await this.pollResearchStatus(company);

          await this.fetchAndUpdateCompany(company.company_id);
          this.showSuccess("Company research completed!");
          await this.checkPotentialDuplicates(company);
        } catch (err) {
          errorLogger.logFailedTo("research company", err);
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
      isSendingMessage(company) {
        if (this.loading) return false;
        if (!company) return false;
        return this.sendingMessages.has(company.name);
      },

      async scanEmails(maxMessages = 10) {
        try {
          // Use the shared email scanning service
          await emailScanningService.scanRecruiterEmails(false); // Default to no research
          await this.pollEmailScanStatus();
        } catch (err) {
          errorLogger.logFailedTo("scan recruiter emails", err);
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

          // After refreshing, check potential duplicates for companies
          try {
            const companies = Array.isArray(this.companies)
              ? this.companies
              : [];
            for (const company of companies) {
              await this.checkPotentialDuplicates(company);
            }
          } catch (err) {
            errorLogger.logFailedTo(
              "check potential duplicates after email scan",
              err
            );
          }
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
          const data = await companiesService.importCompanies();
          this.importTaskId = data.task_id;
          console.log("Import task created with ID:", this.importTaskId);

          // Start polling for task status via shared polling service
          taskPollingService.pollImportCompaniesStatus(this);
        } catch (error) {
          errorLogger.logError("Error starting import:", error);
          this.importingCompanies = false;
          this.importError = error.message;
          this.showError(`Failed to start import: ${error.message}`);
        }
      },

      get filteredCompanies() {
        return filterCompanies(this.companies, this.filterMode);
      },

      get sortedAndFilteredCompanies() {
        return sortCompanies(
          this.filteredCompanies,
          this.sortField,
          this.sortAsc
        );
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
          const updatedCompany = await companiesService.getCompany(companyId);
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
          errorLogger.logError("Error fetching individual company:", err);
        }
      },

      async refreshAllCompanies(includeAll = false) {
        console.log("Refreshing all companies");
        try {
          const data = await companiesService.getCompanies(includeAll);
          console.log("Got companies json response");
          this.companies = normalizeCompanies(data);
          return data;
        } catch (err) {
          errorLogger.logFailedTo("refresh companies", err);
          return [];
        }
      },

      // Toggle archived companies visibility
      async toggleShowArchived() {
        this.showArchived = !this.showArchived;
        await this.refreshAllCompanies(this.showArchived);

        // Update URL to reflect the change
        const url = urlUtils.createUrl();
        setIncludeAllParam(url, this.showArchived);
        window.history.replaceState({}, "", url);
      },

      formatResearchErrors: utilFormatResearchErrors,

      async ignoreAndArchive(company) {
        if (!company) {
          this.showError("No company selected");
          return;
        }

        // Confirm with the user before proceeding
        if (!confirmDialogs.archiveWithoutReply()) {
          return;
        }

        try {
          // Get the message ID from the company's recruiter message
          const messageId = company.recruiter_message?.message_id;

          if (!messageId) {
            this.showError("No message ID found for this company");
            return;
          }

          // Call the archive endpoint via service
          await companiesService.archiveMessage(messageId);

          // Fetch fresh company data
          await this.fetchAndUpdateCompany(company.company_id);

          this.showSuccess("Message archived without reply");
          this.cancelEdit();
        } catch (err) {
          errorLogger.logFailedTo("archive message", err);
          this.showError(
            err.message || "Failed to archive message. Please try again."
          );
        }
      },

      async togglePromising(company, value) {
        if (!company) return;

        // If clicking the same value that's already set, clear it
        if (company.promising === value) {
          value = null;
        }

        const originalValue = company.promising;
        company.promising = value;

        try {
          await companiesService.updateCompanyDetails(company.company_id, {
            promising: value,
          });
        } catch (err) {
          errorLogger.logFailedTo("update promising status", err);
          // Revert the local change if the server update failed
          company.promising = originalValue;
        }
      },

      showResearchCompanyModal() {
        console.log("showResearchCompanyModal called");
        modalUtils.showModal(modalUtils.modalIds.RESEARCH_COMPANY);
        this.researchCompanyForm = {
          url: "",
          name: "",
        };
        console.log("Modal form reset");
      },

      closeResearchCompanyModal() {
        modalUtils.closeModal(modalUtils.modalIds.RESEARCH_COMPANY);
      },

      showImportCompaniesModal() {
        // Show the import companies modal dialog
        modalUtils.showModal(modalUtils.modalIds.IMPORT_COMPANIES);
      },

      closeImportCompaniesModal() {
        // Close the import companies modal dialog
        modalUtils.closeModal(modalUtils.modalIds.IMPORT_COMPANIES);
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

          const data = await companiesService.submitResearch(
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
          errorLogger.logFailedTo("research company", err);
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
          const data = await companiesService.pollResearchTask(
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
          errorLogger.logError("Error polling research task", err);
          this.showError(
            "Failed to check research status. Please refresh the page."
          );
          this.researchCompanyTaskId = null;
        }
      },

      // Alias management
      newAlias: "",
      setAsCanonical: true,

      async addAlias(companyId) {
        if (!this.newAlias.trim()) {
          this.showError("Please enter an alias name");
          return;
        }

        try {
          const payload = {
            alias: this.newAlias.trim(),
            set_as_canonical: this.setAsCanonical,
          };

          await companiesService.addAlias(companyId, payload);

          // Clear the form
          this.newAlias = "";
          this.setAsCanonical = true;

          // Refresh the company data to show the new alias
          await this.fetchAndUpdateCompany(companyId);

          this.showSuccess("Alias added successfully!");
        } catch (err) {
          errorLogger.logFailedTo("add alias", err);
          this.showError(
            err.message || "Failed to add alias. Please try again."
          );
        }
      },
    };
  });
});
