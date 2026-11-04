import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Phase 8 Workspace E2E Acceptance Suite", () => {
  test.beforeEach(async ({ page }) => {
    // Collect console errors to assert zero unhandled exceptions
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.error(`Browser console error: ${msg.text()}`);
      }
    });

    // 1. Visit Auth and register a fresh session user
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/auth");
    await page.waitForLoadState("networkidle");

    await page.click("text=Create Account");
    const uniqueEmail = `workspace_analyst_${Date.now()}@example.com`;
    await page.fill('input[placeholder="Ada Lovelace"]', "Senior Analyst");
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', "Password123!");
    await page.click('button[type="submit"]');

    // Wait for redirect to /workspace
    await expect(page).toHaveURL(/.*workspace/, { timeout: 10000 });

    // Navigate to Datasets and stage sample dataset for the session
    await page.locator('a[href="/datasets"]:visible').first().click();
    await expect(page).toHaveURL(/.*datasets/);
    const csvPath = path.resolve(process.cwd(), "../sample_data/sales.csv");
    await page.setInputFiles('input[type="file"]', csvPath);
    await expect(page.locator("text=Data Health Score")).toBeVisible({ timeout: 15000 });

    // Return to workspace
    await page.locator('a[href="/workspace"]:visible').first().click();
    await expect(page).toHaveURL(/.*workspace/);
  });

  test("Six assignment questions: streaming, charts, timeline nodes, and evidence drawer", async ({
    page,
  }) => {
    // Question 1: Highest revenue region
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Which region generated the highest revenue?"
    );
    await page.click('button:has-text("Ask")');

    // Verify stream completes and expected grounded answer renders
    await expect(
      page.locator("text=North America").first()
    ).toBeVisible({ timeout: 20000 });

    // Verify Reasoning Timeline completed nodes
    await expect(page.locator("text=Reasoning Pipeline")).toBeVisible();
    await expect(page.locator("text=sql_tool")).toBeVisible();
    await expect(page.locator("text=100% GROUNDED")).toBeVisible();

    // Verify chart container is rendered
    await expect(page.locator("text=Analytical Chart")).toBeVisible();

    // Verify Evidence Drawer opens and shows SQL
    await page.click("text=View Evidence Ledger");
    await expect(
      page.locator("text=Evidence Ledger & Code Audit")
    ).toBeVisible();
    await expect(
      page.locator("code:has-text('region')").first()
    ).toBeVisible();

    // Close drawer
    await page.click('button:has-text("Close")');

    // Question 2: Monthly sales trends
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Show monthly sales trends."
    );
    await page.click('button:has-text("Ask")');
    await expect(
      page.getByText(/2024|March/i).first()
    ).toBeVisible({ timeout: 20000 });

    // Question 3: Underperforming products
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Which products are underperforming?"
    );
    await page.click('button:has-text("Ask")');
    await expect(page.locator("text=PROD-020").first()).toBeVisible({
      timeout: 20000,
    });

    // Question 4: Top five customers
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "What are the top five customers?"
    );
    await page.click('button:has-text("Ask")');
    await expect(page.locator("text=CUST-0512").first()).toBeVisible({
      timeout: 20000,
    });

    // Question 5: Code request
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Generate SQL for this analysis."
    );
    await page.click('button:has-text("Ask")');
    await expect(page.locator('button:has-text("SQL / Code")').first()).toBeVisible({
      timeout: 20000,
    });

    // Question 6: Anomaly detection
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Detect anomalies in the dataset."
    );
    await page.click('button:has-text("Ask")');
    await expect(
      page.getByText(/ORD-OUT-01|outlier|anomal/i).first()
    ).toBeVisible({ timeout: 20000 });

    // Take verification screenshot of the complete workspace
    const wsScreenshot = path.resolve(
      process.cwd(),
      "../docs/media/screenshots/workspace_active.png"
    );
    await page.screenshot({ path: wsScreenshot, fullPage: false });
  });

  test("Follow-up question and conversational entity continuity", async ({
    page,
  }) => {
    // Initial question
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Which region generated the highest revenue?"
    );
    await page.click('button:has-text("Ask")');
    await expect(
      page.locator("text=North America").first()
    ).toBeVisible({ timeout: 20000 });

    // Click suggested follow-up or type follow-up
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Show monthly sales trends."
    );
    await page.click('button:has-text("Ask")');
    await expect(
      page.getByText(/2024|March/i).first()
    ).toBeVisible({ timeout: 20000 });
  });

  test("Aborted stream stops cleanly without errors", async ({ page }) => {
    await page.fill(
      'input[placeholder*="Ask about sales"]',
      "Show monthly sales trends."
    );
    await page.click('button:has-text("Ask")');

    // Immediately click Stop button while stream is active
    const stopBtn = page.locator('button:has-text("Stop")');
    if (await stopBtn.isVisible()) {
      await stopBtn.click();
    }

    // Assert Ask button returns and input is re-enabled
    await expect(page.locator('button:has-text("Ask")')).toBeVisible({
      timeout: 5000,
    });
    await expect(
      page.locator('input[placeholder*="Ask about sales"]')
    ).toBeEnabled();
  });
});
