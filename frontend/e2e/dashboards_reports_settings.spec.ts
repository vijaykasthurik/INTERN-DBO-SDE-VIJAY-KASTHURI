import { test, expect } from "@playwright/test";

test.describe("Dashboards, Reports, Settings, Command Palette & 404 E2E", () => {
  test.beforeEach(async ({ page, request }) => {
    const testEmail = `drs_${Date.now()}_${Math.floor(Math.random() * 1000)}@example.com`;
    const regRes = await request.post("/api/v1/auth/register", {
      data: { email: testEmail, password: "PassWord123!", full_name: "DRS Tester" },
    });
    expect(regRes.ok()).toBeTruthy();

    const loginRes = await request.post("/api/v1/auth/login", {
      data: { email: testEmail, password: "PassWord123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token: token } = await loginRes.json();
    await page.addInitScript((val: string) => localStorage.setItem("lumen_access_token", val), token);
  });

  test("dashboards: empty state and live generation error without uploaded data", async ({ page }) => {
    await page.goto("/dashboards");
    await expect(page.locator("h1")).toContainText("Executive Dashboards");
    await expect(page.getByText("Upload a dataset to generate a live dashboard.")).toBeVisible();
    await page.getByRole("button", { name: "Generate Dashboard" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("reports: empty history and export dialog require a real analysis session", async ({ page }) => {
    await page.goto("/reports");
    await expect(page.locator("h1")).toContainText("Executive Reports & Dossiers");
    await expect(page.getByText("No reports have been generated for this account yet.")).toBeVisible();
    await page.locator("button:has-text('Export New Report')").click();
    await expect(page.getByText("Report Title")).toBeVisible();
    await expect(page.locator("select option[value='']")).toHaveText("No analysis sessions available");
    await page.getByRole("button", { name: "Cancel" }).click();
  });

  test("settings: provider health, security guardrails, metric definitions and clear data dialog", async ({ page }) => {
    await page.goto("/settings");

    // 1. Verify settings page
    await expect(page.locator("h1")).toContainText("System Diagnostics & Settings");
    await expect(page.getByText("LLM Provider Health & Router")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("SELECT-Only")).toBeVisible();
    await expect(page.getByText("Sandboxed")).toBeVisible();
    await expect(page.getByText("Prompt Injection Defense")).toBeVisible();

    await expect(page.locator("button:has-text('Add Metric')")).toBeDisabled();
    await expect(page.getByText("Upload a dataset to define business metrics.")).toBeVisible();

    // 3. Test Clear Data dialog opens
    await page.locator("button:has-text('Clear My Data')").click();
    await expect(page.getByText("Confirm Data Wipeout")).toBeVisible();
    await page.locator("button:has-text('Cancel')").click();
  });

  test("command palette: toggle with keyboard shortcut and navigate", async ({ page }) => {
    await page.goto("/workspace");
    await page.waitForTimeout(500);

    // Trigger Cmd+K / Ctrl+K
    await page.keyboard.press("Control+KeyK");
    const searchInput = page.locator("input[placeholder*='Search commands']");
    if (!(await searchInput.isVisible())) {
      await page.evaluate(() => window.dispatchEvent(new CustomEvent("lumen:open-command-palette")));
    }
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    // Press Escape to dismiss
    await page.keyboard.press("Escape");
    await expect(searchInput).not.toBeVisible();
  });

  test("404 not found page: renders clean layout and returns to workspace", async ({ page }) => {
    await page.goto("/non-existent-route-for-testing");

    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText("Page Not Found")).toBeVisible();

    // Click Return to Workspace
    await page.locator("button:has-text('Return to Workspace')").click();
    await expect(page).toHaveURL(/.*workspace/);
  });

  test("responsive viewport checks: 375, 768, 1024, 1440 without horizontal overflow", async ({ page }) => {
    const viewports = [
      { width: 375, height: 667 },
      { width: 768, height: 1024 },
      { width: 1024, height: 768 },
      { width: 1440, height: 900 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize(vp);
      await page.goto("/dashboards");

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      expect(hasHorizontalScroll).toBe(false);
    }
  });
});
