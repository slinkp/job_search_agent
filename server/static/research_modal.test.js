import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

describe("Research Company Modal", () => {
  let Alpine;

  // Import Alpine.js once before all tests
  beforeAll(async () => {
    Alpine = (await import("alpinejs")).default;
    window.Alpine = Alpine;
    Alpine.start();
  });

  beforeEach(async () => {
    // Mock fetch
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ task_id: "test-task-id", status: "pending" }),
      })
    );

    // Set up document body before importing Alpine
    document.body.innerHTML = `
      <main class="container" x-data="companyList">
        <div class="research-company">
          <button @click="showResearchCompanyModal()" class="outline">
            Research a Company
          </button>
        </div>

        <!-- Research Company Modal -->
        <dialog id="research-company-modal">
          <article>
            <h2>Research a Company</h2>
            <form @submit.prevent="submitResearchCompany()">
              <div class="form-group">
                <label for="company-url">Company URL</label>
                <input type="url" id="company-url" x-model="researchCompanyForm.url" placeholder="https://example.com">
                <small>Enter the company's website URL</small>
              </div>
              <div class="form-group">
                <label for="company-name">Company Name (optional)</label>
                <input type="text" id="company-name" x-model="researchCompanyForm.name" placeholder="Company Name">
                <small>If you know the company name, enter it here</small>
              </div>
              <div class="form-actions">
                <button type="button" @click="closeResearchCompanyModal()" class="outline">Cancel</button>
                <button type="submit" :disabled="researchingCompany">
                  <span class="loading-spinner" x-show="researchingCompany"></span>
                  Research Company
                </button>
              </div>
            </form>
          </article>
        </dialog>
      </main>
    `;

    // Initialize Alpine.js with the actual component data
    Alpine.data("companyList", () => ({
      companies: [],
      loading: false,
      researchingCompany: false,
      researchCompanyForm: {
        url: "",
        name: "",
      },
      researchCompanyTaskId: null,
      showError: vi.fn(),
      showSuccess: vi.fn(),

      showResearchCompanyModal() {
        document.getElementById("research-company-modal").showModal();
        this.researchCompanyForm = {
          url: "",
          name: "",
        };
      },

      closeResearchCompanyModal() {
        document.getElementById("research-company-modal").close();
      },

      async submitResearchCompany() {
        try {
          // Validate form
          if (!this.researchCompanyForm.url && !this.researchCompanyForm.name) {
            this.showError("Please provide either a company URL or name");
            return;
          }

          this.researchingCompany = true;

          // Prepare request body
          const body = {};
          if (this.researchCompanyForm.url) {
            body.url = this.researchCompanyForm.url;
          }
          if (this.researchCompanyForm.name) {
            body.name = this.researchCompanyForm.name;
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

          this.closeResearchCompanyModal();
          this.showSuccess(
            "Company research started. This may take a few minutes."
          );

          this.pollResearchCompanyTask();
        } catch (err) {
          console.error("Failed to research company:", err);
          this.showError(
            err.message || "Failed to start research. Please try again."
          );
        } finally {
          this.researchingCompany = false;
        }
      },

      pollResearchCompanyTask: vi.fn(),
    }));

    // Wait for Alpine to process initial state
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  // Clean up after each test
  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  // Clean up after all tests
  afterAll(() => {
    delete window.Alpine;
  });

  it("opens when clicking the research button", async () => {
    const button = document.querySelector(".research-company button");
    const modal = document.getElementById("research-company-modal");
    const showModalSpy = vi.spyOn(modal, "showModal");

    // Click the research button
    button.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Modal should be opened using showModal()
    expect(showModalSpy).toHaveBeenCalled();
  });

  it("closes when clicking the cancel button", async () => {
    const modal = document.getElementById("research-company-modal");
    const cancelButton = modal.querySelector('button[type="button"]');
    const closeSpy = vi.spyOn(modal, "close");

    // Open the modal first
    modal.showModal();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Click cancel
    cancelButton.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Modal should be closed using close()
    expect(closeSpy).toHaveBeenCalled();
  });

  it("validates form input and shows error message", async () => {
    const modal = document.getElementById("research-company-modal");
    const form = modal.querySelector("form");
    let component;

    // Get access to the Alpine component
    Alpine.nextTick(() => {
      component = Alpine.$data(modal.closest("[x-data]"));
    });
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Try to submit with empty form
    form.dispatchEvent(new Event("submit"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith(
      "Please provide either a company URL or name"
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows loading state during submission and success message after", async () => {
    const modal = document.getElementById("research-company-modal");
    const form = modal.querySelector("form");
    let component;

    // Get access to the Alpine component and wait for it to be ready
    await new Promise((resolve) => {
      Alpine.nextTick(() => {
        component = Alpine.$data(modal.closest("[x-data]"));
        resolve();
      });
    });

    // Mock fetch to be slow so we can check loading state
    global.fetch = vi.fn(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    task_id: "test-task-id",
                    status: "pending",
                  }),
              }),
            100
          )
        )
    );

    // Set valid URL and submit
    component.researchCompanyForm.url = "https://example.com";

    // Start submission
    const submitPromise = new Promise((resolve) => {
      // Check loading state after submission starts but before it completes
      setTimeout(() => {
        expect(component.researchingCompany).toBe(true);
        resolve();
      }, 50);
    });

    // Submit form
    form.dispatchEvent(new Event("submit"));

    // Wait for our loading state check
    await submitPromise;

    // Wait for fetch to complete
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Should show success message and be done loading
    expect(component.showSuccess).toHaveBeenCalledWith(
      "Company research started. This may take a few minutes."
    );
    expect(component.pollResearchCompanyTask).toHaveBeenCalled();
    expect(component.researchingCompany).toBe(false);
  });

  it("handles API errors properly", async () => {
    // Mock fetch to return an error
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: "API Error" }),
      })
    );

    const modal = document.getElementById("research-company-modal");
    const form = modal.querySelector("form");
    let component;

    // Get access to the Alpine component and wait for it to be ready
    await new Promise((resolve) => {
      Alpine.nextTick(() => {
        component = Alpine.$data(modal.closest("[x-data]"));
        resolve();
      });
    });

    // Submit with valid data
    component.researchCompanyForm.url = "https://example.com";
    form.dispatchEvent(new Event("submit"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Should show error message
    expect(component.showError).toHaveBeenCalledWith("API Error");
    expect(component.researchingCompany).toBe(false);
  });
});
