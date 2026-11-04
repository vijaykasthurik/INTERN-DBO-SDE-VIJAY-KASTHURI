import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Lumen Frontend Smoke & Visual Responsiveness", () => {
  test("Landing page responsive check at 375, 768, 1440 and visual screenshots", async ({ page }) => {
    const viewports = [
      { name: "mobile_375", width: 375, height: 667 },
      { name: "tablet_768", width: 768, height: 1024 },
      { name: "desktop_1440", width: 1440, height: 900 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await page.waitForLoadState("networkidle");

      // Verify no horizontal overflow
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      expect(hasHorizontalScroll).toBe(false);

      // Verify Brand & Hero
      await expect(page.locator("h1:has-text('Instant clarity')")).toBeVisible();
      await expect(page.locator("text=Lumen").locator("visible=true").first()).toBeVisible();

      // Capture screenshot
      const screenshotPath = path.resolve(
        process.cwd(),
        `../docs/media/screenshots/landing_${vp.name}.png`
      );
      await page.screenshot({ path: screenshotPath, fullPage: false });
    }
  });

  test("Registration -> Login -> Upload dataset -> View profile & health score", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });

    // 1. Visit Auth Page
    await page.goto("/auth");
    await page.waitForLoadState("networkidle");

    // Click 'Create Account' tab
    await page.click("text=Create Account");

    const uniqueEmail = `testuser_${Date.now()}@example.com`;
    const password = "Password123!";
    const fullName = "Test Engineer";

    // Fill registration
    await page.fill('input[placeholder="Ada Lovelace"]', fullName);
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');

    // Should redirect to /workspace
    await expect(page).toHaveURL(/.*workspace/, { timeout: 10000 });

    // 2. Navigate to Datasets page
    await page.locator('a[href="/datasets"]:visible').first().click();
    await expect(page).toHaveURL(/.*datasets/);

    // Upload sales.csv
    const csvPath = path.resolve(process.cwd(), "../sample_data/sales.csv");
    await page.setInputFiles('input[type="file"]', csvPath);

    // Verify dataset card and health score appear
    await expect(page.locator("text=Data Health Score")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Columns & Statistical Schema")).toBeVisible({ timeout: 15000 });

    // Verify quality breakdown expansion
    await page.click("text=View Quality Breakdown");
    await expect(page.locator("text=Duplicate Rows")).toBeVisible({ timeout: 15000 });

    // Take verification screenshot of Datasets screen
    const datasetsScreenshot = path.resolve(
      process.cwd(),
      "../docs/media/screenshots/datasets_profile.png"
    );
    await page.screenshot({ path: datasetsScreenshot, fullPage: false });
  });
});
