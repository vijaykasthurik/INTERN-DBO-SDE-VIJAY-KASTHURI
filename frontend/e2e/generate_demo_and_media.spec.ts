import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.use({
  video: {
    mode: "on",
    size: { width: 1440, height: 900 },
  },
  viewport: { width: 1440, height: 900 },
});

test("Generate official media assets: 10 screenshots and interactive video", async ({ page, request }, testInfo) => {
  test.setTimeout(180000);
  const sampleDir = path.resolve(process.cwd(), "../sample_data");
  const screenshotsDir = path.resolve(process.cwd(), "../docs/media/screenshots");
  fs.mkdirSync(screenshotsDir, { recursive: true });

  // 1. Public Home
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, "landing_hero.png") });
  await page.screenshot({ path: path.join(screenshotsDir, "home.png") });

  // 2. How It Works
  await page.goto("/how-it-works");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(screenshotsDir, "how_it_works.png") });

  // 3. About
  await page.goto("/about");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(screenshotsDir, "about.png") });

  // 4. Contact
  await page.goto("/contact");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(screenshotsDir, "contact.png") });

  // 5. Auth / Register
  const email = `demo_analyst_${Date.now()}@lumen.ai`;
  const password = "Password123!";
  const reg = await request.post("/api/v1/auth/register", {
    data: { email, password, full_name: "Lumen Lead Analyst" },
  });
  expect(reg.ok()).toBeTruthy();

  const login = await request.post("/api/v1/auth/login", {
    data: { email, password },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token: token } = await login.json();
  await page.addInitScript((val: string) => localStorage.setItem("lumen_access_token", val), token);

  // 6. Datasets & Upload
  await page.goto("/datasets");
  await page.waitForLoadState("networkidle");
  const fileInput = page.locator('input[type="file"]');
  await fileInput.waitFor({ state: "attached", timeout: 15000 });
  await fileInput.setInputFiles([
    path.join(sampleDir, "sales.csv"),
    path.join(sampleDir, "customers.csv"),
    path.join(sampleDir, "products.csv"),
  ]);

  // Wait for upload completion and data health score
  await expect(page.getByText("Data Health Score").first()).toBeVisible({ timeout: 25000 });
  await page.screenshot({ path: path.join(screenshotsDir, "datasets_profile.png") });

  // Preview rows modal
  const previewBtn = page.getByRole("button", { name: "Preview Rows" }).first();
  if (await previewBtn.isVisible()) {
    await previewBtn.click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(screenshotsDir, "datasets_preview.png") });
    await page.getByRole("dialog").getByRole("button", { name: "Close dialog" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }

  // 7. Dashboards
  await page.goto("/dashboards");
  await expect(page.getByText("Files analyzed")).toBeVisible({ timeout: 25000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, "dashboards_combined.png") });
  await page.screenshot({ path: path.join(screenshotsDir, "dashboards_executive.png") });

  // Switch to single-file dashboard (sales.csv)
  const salesTab = page.getByRole("button", { name: "sales.csv" });
  if (await salesTab.isVisible()) {
    await salesTab.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(screenshotsDir, "dashboards_single.png") });
  }

  // 8. Workspace & Chat
  await page.goto("/workspace");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);

  const composer = page.locator('input[placeholder*="Ask about sales"]');
  await expect(composer).toBeVisible({ timeout: 15000 });
  await composer.fill("What is in these 3 files? Explain each one.");
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Ask" }).click();

  // Wait for answer completion
  const sqlBtn = page.getByRole("button", { name: "SQL / Code" }).last();
  await sqlBtn.waitFor({ state: "visible", timeout: 45000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(screenshotsDir, "workspace_active.png") });

  // Open Evidence Drawer
  await sqlBtn.click();
  await expect(page.getByRole("heading", { name: "Evidence Ledger & Code Audit" })).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(screenshotsDir, "workspace_evidence_drawer.png") });

  // Close Evidence Drawer
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.waitForTimeout(500);

  // 9. Reports & PDF Export
  await page.goto("/reports");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);

  // Export PDF
  await page.getByRole("button", { name: "Export New Report" }).click();
  await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });
  await page.getByText("PDF Document", { exact: true }).click();
  const pdfDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Generate & Export" }).click();
  const downloadedPdf = await pdfDownload;
  expect(downloadedPdf).toBeTruthy();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, "reports_preview.png") });
  await page.screenshot({ path: path.join(screenshotsDir, "reports_dossier.png") });

  // 10. Profile & Connect AI Popup
  await page.goto("/profile");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);

  // Click on "Connect your AI" or AI model chip in navbar
  const aiButton = page.getByRole("button", { name: /Shared AI|Connect your AI/i }).first();
  if (await aiButton.isVisible()) {
    await aiButton.click();
    await page.waitForTimeout(600);
  }
  await page.screenshot({ path: path.join(screenshotsDir, "profile_connect_model.png") });
  await page.screenshot({ path: path.join(screenshotsDir, "settings_diagnostics.png") });

  // Save video file path
  await page.waitForTimeout(1000);
});
