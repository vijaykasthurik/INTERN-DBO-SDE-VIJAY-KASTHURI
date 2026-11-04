import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.describe("Full Application Control & Interaction Suite", () => {
  const sampleDir = path.resolve(process.cwd(), "../sample_data");

  test("1. Public navigation and contact submission across viewports", async ({ page }) => {
    for (const width of [375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });

      // Landing
      await page.goto("/");
      await expect(page.getByRole("navigation", { name: "Public navigation" })).toBeVisible();

      // How it works
      await page.goto("/how-it-works");
      await expect(page.getByRole("heading", { name: "How Lumen works", exact: true })).toBeVisible();

      // About
      await page.goto("/about");
      await expect(page.getByRole("heading", { name: "Analysis with a visible evidence trail", exact: true })).toBeVisible();

      // Contact form
      await page.goto("/contact");
      await expect(page.getByRole("heading", { name: "Contact", exact: true })).toBeVisible();
      await page.getByLabel("Name", { exact: true }).fill("Quality Auditor");
      await page.getByLabel("Email", { exact: true }).fill("auditor@lumen.ai");
      await page.getByLabel("Message", { exact: true }).fill("Automated e2e control check message.");

      if (width === 1440) {
        await page.getByRole("button", { name: "Send message" }).click();
        await expect(page.locator('[role="status"], [role="alert"]')).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test("2. Complete signed-in user lifecycle, controls, drawers, modals, and downloads", async ({
    page,
    request,
  }) => {
    test.setTimeout(120000);

    // Register & Login
    const testEmail = `all_controls_${Date.now()}@example.com`;
    const regRes = await request.post("/api/v1/auth/register", {
      data: { email: testEmail, password: "PassWord123!", full_name: "Control Auditor" },
    });
    expect(regRes.ok()).toBeTruthy();

    const loginRes = await request.post("/api/v1/auth/login", {
      data: { email: testEmail, password: "PassWord123!" },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token: token } = await loginRes.json();
    await page.addInitScript((val: string) => localStorage.setItem("lumen_access_token", val), token);

    // Create session for workspace
    const sessRes = await request.post("/api/v1/chat/sessions", {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: "Control Audit Session" },
    });
    expect(sessRes.status()).toBe(201);

    // --- UPLOAD FILES ---
    await page.goto("/datasets");
    await page.locator('input[type="file"]').waitFor({ state: "attached", timeout: 15000 });
    await page.locator('input[type="file"]').setInputFiles([
      path.join(sampleDir, "sales.csv"),
      path.join(sampleDir, "customers.csv"),
      path.join(sampleDir, "products.csv"),
    ]);

    // Upload auto-navigates to /dashboards
    await expect(page.getByText("Files analyzed")).toBeVisible({ timeout: 25000 });

    // --- DASHBOARDS PAGE ---
    // Test dataset switcher pill
    await page.getByRole("button", { name: "sales.csv" }).click();
    await expect(page.getByText("Total net_revenue")).toBeVisible({ timeout: 10000 });

    // Export PDF from Dashboard
    const dashDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export PDF" }).click();
    const dashPdf = await dashDownload;
    const dashPdfPath = await dashPdf.path();
    expect(dashPdfPath).toBeTruthy();
    expect(fs.statSync(dashPdfPath!).size).toBeGreaterThan(1000);

    // --- DATASETS PAGE ---
    await page.goto("/datasets");
    await expect(page.getByText("Data Health Score").first()).toBeVisible({ timeout: 15000 });

    // Test Paginated Preview Modal
    const previewBtn = page.getByRole("button", { name: "Preview Rows" }).first();
    await previewBtn.waitFor({ state: "visible" });
    await previewBtn.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText(/rows total/)).toBeVisible();
    const nextBtn = page.getByRole("button", { name: "Next" });
    await expect(nextBtn).toBeVisible();
    await nextBtn.click();
    await page.getByRole("dialog").getByRole("button", { name: "Close dialog" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);

    // --- WORKSPACE CHAT & EVIDENCE DRAWER ---
    await page.goto("/workspace");
    await expect(page.locator('input[placeholder*="Ask about sales"]')).toBeVisible({ timeout: 15000 });

    // Ask Question
    await page.locator('input[placeholder*="Ask about sales"]').fill("What were the total sales by region?");
    await page.getByRole("button", { name: "Ask" }).click();

    // Verify response streams in and Evidence Drawer button is active
    const sqlCodeBtn = page.getByRole("button", { name: "SQL / Code" }).last();
    await sqlCodeBtn.waitFor({ state: "visible", timeout: 30000 });
    await sqlCodeBtn.click();

    // Evidence Ledger Drawer inspection
    await expect(page.getByRole("heading", { name: "Evidence Ledger & Code Audit" })).toBeVisible();
    const runSqlBtn = page.getByRole("button", { name: "Run SQL" });
    await runSqlBtn.click();
    await expect(page.getByText(/Validated query completed/)).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: "Close", exact: true }).click();

    // --- REPORTS PAGE ---
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Executive Reports & Dossiers" })).toBeVisible({ timeout: 15000 });

    // Generate New Markdown Report
    await page.getByRole("button", { name: "Export New Report" }).click();
    await page.getByText("Markdown", { exact: true }).click();
    const mdDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "Generate & Export" }).click();
    const mdFile = await mdDownload;
    const mdContent = fs.readFileSync((await mdFile.path())!, "utf-8");
    expect(mdContent).toContain("Evidence Ledger");

    // Preview Existing Report
    await expect(page.getByRole("button", { name: "Preview" }).first()).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: "Preview" }).first().click();
    await expect(page.locator("iframe[title], pre")).toBeVisible();
    await page.getByRole("button", { name: "Close dialog" }).click();

    // Download PDF from Reports Table
    const repDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download PDF" }).first().click();
    const repPdf = await repDownload;
    expect(fs.statSync((await repPdf.path())!).size).toBeGreaterThan(1000);

    // Delete Report
    const deleteResPromise = page.waitForResponse((r) => r.url().includes("/api/v1/reports") && r.request().method() === "DELETE");
    const initialReportCount = await page.getByRole("button", { name: "Delete report" }).count();
    await page.getByRole("button", { name: "Delete report" }).first().click();
    await deleteResPromise;
    await expect(page.getByRole("button", { name: "Delete report" })).toHaveCount(initialReportCount - 1);

    // --- PROFILE / BYOK PAGE ---
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Account & AI Connections" })).toBeVisible({ timeout: 15000 });

    // Check fallback toggle
    const fallbackSwitch = page.locator('button[role="switch"]');
    if (await fallbackSwitch.count() > 0) {
      await fallbackSwitch.click();
      await page.waitForTimeout(300);
      await fallbackSwitch.click();
    }

    // --- SETTINGS PAGE ---
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "System Diagnostics & Settings" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("LLM Provider Health & Router")).toBeVisible();

    // Metric definition addition
    await page.getByRole("button", { name: "Add Metric" }).click();
    await page.locator('input[placeholder="e.g. gross_profit_margin"]').fill("total_quantity");
    await page.locator('input[placeholder="e.g. SUM(revenue - cost) / SUM(revenue)"]').fill("SUM(quantity)");
    await page.locator('input[placeholder="Explain how this metric should be interpreted"]').fill("Sum of units across transactions");
    await page.getByRole("button", { name: "Save Metric" }).click();
    await expect(page.getByText("total_quantity")).toBeVisible({ timeout: 10000 });

    // --- DATASET DELETE VERIFICATION ---
    await page.goto("/datasets");
    const deleteDatasetBtn = page.getByRole("button", { name: "Delete Table" }).first();
    await deleteDatasetBtn.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: /Delete dataset/i }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
});
