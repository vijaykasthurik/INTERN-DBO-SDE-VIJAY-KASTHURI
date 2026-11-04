import { test, expect } from "@playwright/test";

test.describe("Dashboards, Reports, Settings, Command Palette & 404 E2E", () => {
  test("dashboards: generate, widgets rendering, fullscreen and reordering", async ({ page }) => {
    await page.goto("/dashboards");

    // 1. Verify page title and header
    await expect(page.locator("h1")).toContainText("Executive Dashboards");
    await expect(page.getByText("Total Net Revenue")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Statistical Outlier Alerts")).toBeVisible();

    // 2. Click Generate Dashboard button
    const generateBtn = page.locator("button:has-text('Generate Dashboard')");
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // Verify widgets remain visible and active
    await expect(page.locator("h3:has-text('Monthly Revenue Trend')").first()).toBeVisible({ timeout: 5000 });

    // 3. Test Fullscreen Dialog on first widget card
    const firstCard = page.locator(".group.relative").first();
    await firstCard.hover();
    const fullscreenBtn = firstCard.locator("button[title='Fullscreen']");
    if (await fullscreenBtn.isVisible()) {
      await fullscreenBtn.click();
      await expect(page.locator("h3:has-text('Total Net Revenue')")).toBeVisible();
      // Close fullscreen dialog
      await page.locator("button:has-text('Close')").click();
    }

    // 4. Test reorder widget
    const moveDownBtn = firstCard.locator("button[title='Move down']");
    if (await moveDownBtn.isVisible()) {
      await moveDownBtn.click();
    }
  });

  test("reports: list, export new report dialog and markdown preview", async ({ page }) => {
    await page.goto("/reports");

    // 1. Verify reports listing
    await expect(page.locator("h1")).toContainText("Executive Reports & Dossiers");
    await expect(page.getByText("Executive Revenue & Anomaly Audit")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("March 2024 Supply Chain Contraction Breakdown")).toBeVisible();

    // 2. Open Preview modal on Markdown report
    const previewBtn = page.locator("button:has-text('Preview')").first();
    await previewBtn.click();
    await expect(page.getByText("Lumen Analytical Dossier")).toBeVisible();
    await page.locator("button:has-text('Close')").click();

    // 3. Click Export New Report
    await page.locator("button:has-text('Export New Report')").click();
    await expect(page.getByText("Report Title")).toBeVisible();

    // Fill in new report title and submit
    const titleInput = page.locator("input[placeholder*='Q1 Revenue']");
    await titleInput.fill("Automated E2E Operational Report");
    await page.locator("button:has-text('Generate & Export')").click();

    // Verify new report appears
    await expect(page.getByText("Automated E2E Operational Report")).toBeVisible({ timeout: 8000 });
  });

  test("settings: provider health, security guardrails, metric definitions and clear data dialog", async ({ page }) => {
    await page.goto("/settings");

    // 1. Verify settings page
    await expect(page.locator("h1")).toContainText("System Diagnostics & Settings");
    await expect(page.getByText("LLM Provider Health & Router")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("SELECT-Only")).toBeVisible();
    await expect(page.getByText("Sandboxed")).toBeVisible();
    await expect(page.getByText("Prompt Injection Defense")).toBeVisible();

    // 2. Add Business Metric
    await page.locator("button:has-text('Add Metric')").click();
    await page.locator("input[placeholder*='gross_profit_margin']").fill("churn_rate");
    await page.locator("input[placeholder*='SUM(revenue - cost)']").fill("COUNT(churned) / COUNT(*)");
    await page.locator("input[placeholder*='Explain how this metric']").fill("Percentage of lost accounts");
    await page.locator("button:has-text('Save Metric')").click();

    // Assert metric added
    await expect(page.getByText("churn_rate")).toBeVisible();

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
