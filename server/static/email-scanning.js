// Shared Email Scanning Module
// Provides email scanning functionality that can be used by multiple components

export class EmailScanningService {
  constructor() {
    this.scanningEmails = false;
    this.emailScanTaskId = null;
    this.emailScanStatus = null;
    this.emailScanError = null;
  }

  // Scan for new recruiter emails from Gmail
  async scanRecruiterEmails(doResearch = false) {
    if (this.scanningEmails) return;

    try {
      this.scanningEmails = true;
      this.emailScanError = null;

      const response = await fetch("/api/scan_recruiter_emails", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
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

      return data;
    } catch (err) {
      console.error("Failed to scan recruiter emails:", err);
      this.emailScanError = err.message;
      throw err;
    } finally {
      this.scanningEmails = false;
    }
  }

  // Poll for email scan task status
  async pollEmailScanStatus() {
    if (!this.emailScanTaskId) return;

    try {
      const response = await fetch(`/api/tasks/${this.emailScanTaskId}`);
      if (!response.ok) {
        throw new Error(`Failed to get task status: ${response.status}`);
      }

      const task = await response.json();
      this.emailScanStatus = task.status;

      if (task.status === "completed") {
        console.log("Email scan completed successfully");
        this.emailScanTaskId = null;
        return { status: "completed", task };
      } else if (task.status === "failed") {
        console.error("Email scan failed:", task.result);
        this.emailScanError = task.result?.error || "Email scan failed";
        this.emailScanTaskId = null;
        return { status: "failed", task, error: this.emailScanError };
      } else if (task.status === "pending" || task.status === "running") {
        // Continue polling
        setTimeout(() => this.pollEmailScanStatus(), 2000);
        return { status: "polling", task };
      }
    } catch (err) {
      console.error("Failed to poll email scan status:", err);
      this.emailScanError = err.message;
      this.emailScanTaskId = null;
      return { status: "error", error: err.message };
    }
  }

  // Get email scan status text for display
  getEmailScanStatusText() {
    if (this.emailScanError) {
      return `Failed: ${this.emailScanError}`;
    }
    switch (this.emailScanStatus) {
      case "pending":
        return "Starting email scan...";
      case "running":
        return "Scanning recruiter emails... (this may take a while for large fetches)";
      case "completed":
        return "Email scan complete";
      case "failed":
        return "Failed to scan emails";
      default:
        return "";
    }
  }

  // Get email scan status CSS classes
  getEmailScanStatusClass() {
    return {
      "status-pending": this.emailScanStatus === "pending",
      "status-running": this.emailScanStatus === "running",
      "status-completed": this.emailScanStatus === "completed",
      "status-failed": this.emailScanStatus === "failed",
    };
  }

  // Reset the service state
  reset() {
    this.scanningEmails = false;
    this.emailScanTaskId = null;
    this.emailScanStatus = null;
    this.emailScanError = null;
  }
}
