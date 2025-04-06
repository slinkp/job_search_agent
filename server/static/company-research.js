export class CompanyResearchService {
  constructor() {
    this.researchingCompany = false;
    this.researchCompanyTaskId = null;
  }

  async submitResearch(formData) {
    if (!formData.url && !formData.name) {
      throw new Error("Please provide either a company URL or name");
    }

    this.researchingCompany = true;

    try {
      const body = {};
      if (formData.url) {
        body.url = formData.url;
      }
      if (formData.name) {
        body.name = formData.name;
      }

      const response = await fetch("/api/companies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(
          error.error || `Failed to start research: ${response.status}`
        );
      }

      const data = await response.json();
      this.researchCompanyTaskId = data.task_id;
      return data;
    } finally {
      this.researchingCompany = false;
    }
  }

  async pollResearchTask(taskId) {
    if (!taskId) return;

    const response = await fetch(`/api/tasks/${taskId}`);
    if (!response.ok) {
      throw new Error(`Failed to check task status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  }
}
