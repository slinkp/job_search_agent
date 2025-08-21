import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Enable DOM-like environment for tests
    environment: "happy-dom",

    // Enable global test APIs (describe, test, expect)
    globals: true,

    // Setup files to run before tests
    setupFiles: ["./vitest.setup.js"],

    // Configure coverage collection
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        "vitest.setup.js",
        "server/static/index.html",
      ],
      include: [
        "server/static/*.js",
        "server/frontend/**/*.js",
      ],
      thresholds: {
        perFile: {
          "server/static/app.js": { lines: 30 },
          "server/static/daily-dashboard.js": { lines: 35 },
        },
      },
    },

    // Include source files for tests
    include: ["server/frontend/tests/**/*.test.js"],

    // Watch for changes in these directories
    watchExclude: ["node_modules/**", "coverage/**", ".git/**"],

    // In ms.
    testTimeout: 5000,
    hookTimeout: 5000,
    teardownTimeout: 2000,
  },
});
