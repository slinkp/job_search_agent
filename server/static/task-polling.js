export class TaskPollingService {
  constructor({ sleep } = {}) {
    this.researchingCompanies = new Set();
    this.generatingMessages = new Set();
    this.sendingMessages = new Set();
    this._sleep =
      typeof sleep === "function"
        ? sleep
        : (ms) => new Promise((r) => setTimeout(r, ms));
  }

  // Poll for research task status
  async pollResearchStatus(company) {
    return this.pollTaskStatus(company, "research");
  }

  // Poll for message generation task status
  async pollMessageStatus(company) {
    return this.pollTaskStatus(company, "message");
  }

  // Poll for send and archive task status
  async pollSendAndArchiveStatus(taskId) {
    console.log(`Starting poll for send and archive task:`, { taskId });

    while (true) {
      try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const task = await response.json();

        console.log(`Send and archive poll response:`, task);

        if (task.status === "completed" || task.status === "failed") {
          return task;
        }

        await this._sleep(1000);
      } catch (err) {
        console.error(`Failed to poll send and archive status:`, err);
        throw err;
      }
    }
  }

  // Get research status text for display
  getResearchStatusText(company) {
    return this.getTaskStatusText(company, "research");
  }

  // Get message status text for display
  getMessageStatusText(company) {
    return this.getTaskStatusText(company, "message");
  }

  // Get research status CSS classes
  getResearchStatusClass(company) {
    return {
      "status-pending": company.research_status === "pending",
      "status-running": company.research_status === "running",
      "status-completed": company.research_status === "completed",
      "status-failed":
        company.research_status === "failed" || !!company.research_error,
    };
  }

  // Get message status CSS classes
  getMessageStatusClass(company) {
    return {
      "status-pending": company.message_status === "pending",
      "status-running": company.message_status === "running",
      "status-completed": company.message_status === "completed",
      "status-failed":
        company.message_status === "failed" || !!company.message_error,
    };
  }

  // Get the name/key for tracking (works with both company and message objects)
  _getTrackingKey(obj) {
    if (!obj) return "";
    // Message objects have company_name, company objects have name
    return obj.company_name || obj.name || "";
  }

  // Check if company is being researched
  isResearching(company) {
    return this.researchingCompanies.has(this._getTrackingKey(company));
  }

  // Check if message is being generated for company
  isGeneratingMessage(company) {
    if (!company) return false;
    return this.generatingMessages.has(this._getTrackingKey(company));
  }

  // Add company to researching set
  addResearching(company) {
    this.researchingCompanies.add(this._getTrackingKey(company));
  }

  // Remove company from researching set
  removeResearching(company) {
    this.researchingCompanies.delete(this._getTrackingKey(company));
  }

  // Add company to generating messages set
  addGeneratingMessage(company) {
    this.generatingMessages.add(this._getTrackingKey(company));
  }

  // Remove company from generating messages set
  removeGeneratingMessage(company) {
    this.generatingMessages.delete(this._getTrackingKey(company));
  }

  // Add company to sending messages set
  addSendingMessage(company) {
    this.sendingMessages.add(this._getTrackingKey(company));
  }

  // Remove company from sending messages set
  removeSendingMessage(company) {
    this.sendingMessages.delete(this._getTrackingKey(company));
  }

  // Generic task status text generator
  getTaskStatusText(company, taskType) {
    const statusField =
      taskType === "message" ? "message_status" : "research_status";
    const errorField =
      taskType === "message" ? "message_error" : "research_error";
    const status = company[statusField];
    const error = company[errorField];

    if (error) {
      return `Failed: ${error}`;
    }

    switch (status) {
      case "pending":
        return taskType === "message"
          ? "Generating reply..."
          : "Starting research...";
      case "running":
        return taskType === "message"
          ? "Generating reply..."
          : "Researching company...";
      case "completed":
        return taskType === "message" ? "Reply generated" : "Research complete";
      case "failed":
        return taskType === "message"
          ? "Failed to generate reply"
          : "Failed to research company";
      default:
        return "";
    }
  }

  // Generic task polling method
  async pollTaskStatus(company, taskType) {
    const isMessage = taskType === "message";
    const trackingSet = isMessage
      ? this.generatingMessages
      : this.researchingCompanies;
    const taskIdField = isMessage ? "message_task_id" : "research_task_id";
    const statusField = isMessage ? "message_status" : "research_status";
    const errorField = isMessage ? "message_error" : "research_error";

    const taskId = company ? company[taskIdField] : null;
    const trackingKey = this._getTrackingKey(company);

    console.log(`Starting poll for ${taskType}`, {
      companyName: trackingKey,
      taskId,
    });

    while (trackingSet.has(trackingKey)) {
      try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const task = await response.json();

        console.log(`Poll response for ${trackingKey}:`, task);

        // Update the status
        if (company) {
          company[statusField] = task.status;
        }

        if (task.status === "completed" || task.status === "failed") {
          if (task.status === "failed") {
            console.log(`Task failed for ${trackingKey}:`, task.error);
            if (company) {
              company[errorField] = task.error;
            }
          }

          trackingSet.delete(trackingKey);
          break;
        }

        await this._sleep(1000);
      } catch (err) {
        console.error(`Failed to poll ${taskType} status:`, err);
        trackingSet.delete(trackingKey);
        break;
      }
    }
  }

  // Reset the service state
  reset() {
    this.researchingCompanies.clear();
    this.generatingMessages.clear();
    this.sendingMessages.clear();
  }

  // Poll import companies task status, updating the host component's import fields
  async pollImportCompaniesStatus(hostComponent) {
    if (!hostComponent || !hostComponent.importTaskId) return;

    // Ensure initial status exists
    if (
      !hostComponent.importStatus ||
      typeof hostComponent.importStatus !== "object"
    ) {
      hostComponent.importStatus = {
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

    const trackingKey = "import_companies";
    this.sendingMessages.add(trackingKey); // reuse a set for loop control
    try {
      while (this.sendingMessages.has(trackingKey)) {
        const response = await fetch(
          `/api/tasks/${hostComponent.importTaskId}`
        );
        const task = await response.json();

        // Update status snapshot
        hostComponent.importStatus = task.status;

        if (task.result) {
          const current = hostComponent.importStatus;
          hostComponent.importStatus = {
            ...current,
            ...task.result,
            current_company:
              task.result.current_company || current.current_company || "",
            percent_complete:
              task.result.total_found > 0
                ? (task.result.processed / task.result.total_found) * 100
                : 0,
            created: task.result.created ?? current.created ?? 0,
            updated: task.result.updated ?? current.updated ?? 0,
            skipped: task.result.skipped ?? current.skipped ?? 0,
            errors: task.result.errors ?? current.errors ?? 0,
          };
        }

        if (task.status === "completed" || task.status === "failed") {
          // Refresh companies on completion
          await hostComponent.refreshAllCompanies();
          hostComponent.importingCompanies = false;

          if (task.status === "completed") {
            const stats = hostComponent.importStatus || {};
            const msg = `Import completed! Created: ${
              stats.created || 0
            }, Updated: ${stats.updated || 0}, Skipped: ${
              stats.skipped || 0
            }, Errors: ${stats.errors || 0}`;
            if (typeof hostComponent.showSuccess === "function") {
              hostComponent.showSuccess(msg);
            }
          } else {
            hostComponent.importError =
              task.error || "Failed to check task status";
            if (typeof hostComponent.showError === "function") {
              hostComponent.showError(hostComponent.importError);
            }
          }

          this.sendingMessages.delete(trackingKey);
          break;
        }

        await this._sleep(1000);
      }
    } catch (err) {
      this.sendingMessages.delete(trackingKey);
      hostComponent.importError = "Failed to check task status";
      hostComponent.importingCompanies = false;
    }
  }
}
