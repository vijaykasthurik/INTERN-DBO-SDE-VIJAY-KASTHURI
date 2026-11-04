import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts/,
  timeout: 45000,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      port: 8000,
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: "npm run dev",
      cwd: "./",
      port: 5173,
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],
});
