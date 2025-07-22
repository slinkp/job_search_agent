export class TaskPollingService {
  constructor() {
    this.researchingCompanies = new Set();
    this.generatingMessages = new Set();
  }

  // Poll for research task status
  async pollResearchStatus(company) {
    return this.pollTaskStatus(company, "research");
  }

  // Poll for message generation task status
  async pollMessageStatus(company) {
    return this.pollTaskStatus(company, "message");
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

  // Check if company is being researched
  isResearching(company) {
    return this.researchingCompanies.has(company.name);
  }

  // Check if message is being generated for company
  isGeneratingMessage(company) {
    if (!company) return false;
    return this.generatingMessages.has(company.name);
  }

  // Add company to researching set
  addResearching(company) {
    this.researchingCompanies.add(company.name);
  }

  // Remove company from researching set
  removeResearching(company) {
    this.researchingCompanies.delete(company.name);
  }

  // Add company to generating messages set
  addGeneratingMessage(company) {
    this.generatingMessages.add(company.name);
  }

  // Remove company from generating messages set
  removeGeneratingMessage(company) {
    this.generatingMessages.delete(company.name);
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
    const trackingKey = company ? company.name : "";

    console.log(`Starting poll for ${taskType}`, {
      companyName: company?.name,
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

        await new Promise((resolve) => setTimeout(resolve, 1000));
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
  }
}
