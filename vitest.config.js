import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Enable DOM-like environment for tests
    environment: "jsdom",

    // Enable global test APIs (describe, test, expect)
    globals: true,

    // Setup files to run before tests
    setupFiles: ["./vitest.setup.js"],

    // Configure coverage collection
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "vitest.setup.js"],
    },

    // Include source files for tests
    include: ["server/frontend/tests/**/*.test.js"],

    // Watch for changes in these directories
    watchExclude: ["node_modules/**", "coverage/**", ".git/**"],
  },
});
