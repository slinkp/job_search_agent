export class CompaniesService {
  async getCompanies(includeAll = false) {
    const params = new URLSearchParams();
    if (includeAll) {
      params.append("include_all", "true");
    }
    const url = `/api/companies${
      params.toString() ? "?" + params.toString() : ""
    }`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch companies: ${response.status}`);
    }
    return response.json();
  }

  async getCompany(companyId) {
    const response = await fetch(
      `/api/companies/${encodeURIComponent(companyId)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to load company: ${response.status}`);
    }
    return response.json();
  }

  async updateCompanyDetails(companyId, payload) {
    const response = await fetch(
      `/api/companies/${encodeURIComponent(companyId)}/details`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to update company details: ${response.status}`);
    }
    return response.json();
  }

  async saveReply(messageId, replyText) {
    const response = await fetch(`/api/messages/${messageId}/reply`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: replyText }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to save reply: ${response.status}`
      );
    }
    return response.json();
  }

  async loadCompany(companyId) {
    const company = await this.getCompany(companyId);

    // Get associated messages
    const messagesResponse = await fetch(`/api/messages`);
    if (messagesResponse.ok) {
      const allMessages = await messagesResponse.json();
      company.associated_messages = allMessages.filter(
        (msg) => msg.company_id === companyId
      );
    } else {
      company.associated_messages = [];
    }

    return company;
  }

  async loadMessageAndCompany(messageId) {
    // Get message details
    const messagesResponse = await fetch(`/api/messages`);
    if (!messagesResponse.ok) {
      throw new Error(`Failed to load messages: ${messagesResponse.status}`);
    }

    const allMessages = await messagesResponse.json();
    const message = allMessages.find((msg) => msg.message_id === messageId);

    if (!message) {
      throw new Error("Message not found");
    }

    // Get associated company
    const company = await this.getCompany(message.company_id);
    company.associated_messages = allMessages.filter(
      (msg) => msg.company_id === message.company_id
    );

    return { company, message };
  }

  async archiveMessage(messageId) {
    const response = await fetch(`/api/messages/${messageId}/archive`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to archive message: ${response.status}`
      );
    }
    return response.json();
  }

  async sendAndArchive(messageId) {
    const response = await fetch(
      `/api/messages/${messageId}/send_and_archive`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to send and archive: ${response.status}`
      );
    }
    return response.json();
  }

  async generateReply(messageId) {
    const response = await fetch(`/api/messages/${messageId}/reply`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to generate reply: ${response.status}`
      );
    }
    return response.json();
  }

  async research(companyId) {
    const response = await fetch(`/api/companies/${companyId}/research`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to start research: ${response.status}`
      );
    }
    return response.json();
  }

  async importCompanies() {
    const response = await fetch("/api/import_companies", {
      method: "POST",
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || response.statusText);
    }
    return response.json();
  }

  async submitResearch(researchData) {
    const response = await fetch("/api/companies", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(researchData),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to submit research: ${response.status}`
      );
    }
    return response.json();
  }

  async pollResearchTask(taskId) {
    const response = await fetch(`/api/tasks/${taskId}`);
    if (!response.ok) {
      throw new Error(`Failed to poll research task: ${response.status}`);
    }
    return response.json();
  }

  async pollTask(taskId) {
    const response = await fetch(`/api/tasks/${taskId}`);
    if (!response.ok) {
      throw new Error(`Failed to poll task: ${response.status}`);
    }
    return response.json();
  }

  async scanEmails(maxMessages = 10) {
    const response = await fetch("/api/scan_emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ max_messages: maxMessages }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.error || `Failed to scan emails: ${response.status}`
      );
    }
    return response.json();
  }

  async getMessages() {
    const response = await fetch("/api/messages");
    if (!response.ok) {
      throw new Error(`Failed to load messages: ${response.status}`);
    }
    return response.json();
  }
}


