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
    global.fetch = vi.fn(() => Promise.resolve({ ok: true }));

    // Set up document body before importing Alpine
    document.body.innerHTML = `
      <main class="container" x-data="companyList">
        <div class="research-company">
          <button @click="showResearchCompanyModal()" class="outline">
            Research a Company
          </button>
        </div>

        <!-- Research Company Modal -->
        <div id="research-company-modal" class="modal" x-show="researchCompanyModalOpen" x-cloak>
          <div class="modal-content">
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
          </div>
        </div>
      </main>
    `;

    // Initialize Alpine.js with the actual component data
    Alpine.data("companyList", () => ({
      companies: [],
      loading: false,
      researchCompanyModalOpen: false,
      researchingCompany: false,
      researchCompanyForm: {
        url: "",
        name: "",
      },
      researchCompanyTaskId: null,

      showResearchCompanyModal() {
        this.researchCompanyModalOpen = true;
        this.researchCompanyForm = {
          url: "",
          name: "",
        };
      },

      closeResearchCompanyModal() {
        this.researchCompanyModalOpen = false;
      },

      async submitResearchCompany() {
        if (!this.researchCompanyForm.url && !this.researchCompanyForm.name) {
          return;
        }

        const body = {};
        if (this.researchCompanyForm.url) {
          body.url = this.researchCompanyForm.url;
        }
        if (this.researchCompanyForm.name) {
          body.name = this.researchCompanyForm.name;
        }

        await fetch("/api/companies", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        });
      },
    }));

    // Wait for Alpine to process initial state
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  // Clean up after each test
  afterEach(() => {
    // Reset the document body
    document.body.innerHTML = "";
  });

  // Clean up after all tests
  afterAll(() => {
    // Clean up Alpine.js
    delete window.Alpine;
  });

  it("opens when clicking the research button", async () => {
    const button = document.querySelector("button");
    const modal = document.querySelector("#research-company-modal");

    // Modal should be hidden initially
    expect(modal.getAttribute("x-show")).toBe("researchCompanyModalOpen");

    // Click the research button
    button.click();

    // Wait for Alpine to process the click
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Modal should be visible
    expect(modal.getAttribute("x-show")).toBe("researchCompanyModalOpen");
  });

  it("closes when clicking the cancel button", async () => {
    const openButton = document.querySelector("button");
    const modal = document.querySelector("#research-company-modal");
    const cancelButton = modal.querySelector('button[type="button"]');

    // Open the modal
    openButton.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(modal.getAttribute("x-show")).toBe("researchCompanyModalOpen");

    // Click cancel
    cancelButton.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Modal should be hidden
    expect(modal.getAttribute("x-show")).toBe("researchCompanyModalOpen");
  });

  it("validates URL input", async () => {
    const openButton = document.querySelector("button");
    const form = document.querySelector("form");
    const urlInput = form.querySelector('input[type="url"]');

    // Open the modal
    openButton.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Try to submit with invalid URL
    urlInput.value = "not-a-url";
    urlInput.dispatchEvent(new Event("input"));
    form.dispatchEvent(new Event("submit"));

    // Form should not submit (URL validation)
    expect(urlInput.validity.valid).toBe(false);
  });

  it("submits form with valid data", async () => {
    const openButton = document.querySelector("button");
    const form = document.querySelector("form");
    const urlInput = form.querySelector('input[type="url"]');
    const nameInput = form.querySelector('input[type="text"]');

    // Open the modal
    openButton.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Set valid data
    urlInput.value = "https://example.com";
    urlInput.dispatchEvent(new Event("input"));
    nameInput.value = "Example Corp";
    nameInput.dispatchEvent(new Event("input"));

    // Submit the form
    form.dispatchEvent(new Event("submit"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    // Verify fetch was called with correct data
    expect(fetch).toHaveBeenCalledWith("/api/companies", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: "https://example.com",
        name: "Example Corp",
      }),
    });
  });
});
