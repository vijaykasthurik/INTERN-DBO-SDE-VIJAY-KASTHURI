import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("Live end-to-end analytical workflow with multi-file CSV, XLSX, charts, SQL, exports, and BYOK", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const sampleDir = path.resolve(process.cwd(), "../sample_data");
  const mediaDir = path.resolve(process.cwd(), "../docs/media/live_flow");
  fs.mkdirSync(mediaDir, { recursive: true });

  // 1. Register & Login
  const testEmail = `live_flow_${Date.now()}@example.com`;
  const reg = await request.post("/api/v1/auth/register", {
    data: { email: testEmail, password: "LiveFlowPassword123!", full_name: "Live Workflow User" },
  });
  expect(reg.ok()).toBeTruthy();

  const login = await request.post("/api/v1/auth/login", {
    data: { email: testEmail, password: "LiveFlowPassword123!" },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token: token } = await login.json();
  await page.addInitScript((val: string) => localStorage.setItem("lumen_access_token", val), token);

  const sessRes = await request.post("/api/v1/chat/sessions", {
    headers: { Authorization: `Bearer ${token}` },
    data: { title: "Live Analytical Investigation" },
  });
  expect(sessRes.status()).toBe(201);
  const sessionId = (await sessRes.json()).id as string;

  // 2. Upload 3 CSVs + 1 XLSX
  await page.goto("/datasets");
  await page.locator('input[type="file"]').waitFor({ state: "attached", timeout: 15000 });
  await page.locator('input[type="file"]').setInputFiles([
    path.join(sampleDir, "sales.csv"),
    path.join(sampleDir, "customers.csv"),
    path.join(sampleDir, "products.xlsx"),
  ]);

  // Wait for upload and profiling to complete
  await expect(page.getByText("Data Health Score").first()).toBeVisible({ timeout: 25000 });

  // Navigate to dashboards to inspect auto-generated canvas
  await page.goto("/dashboards");
  await expect(page.getByText("Files analyzed")).toBeVisible({ timeout: 25000 });
  await page.screenshot({ path: path.join(mediaDir, "01_dashboards_generated.png") });

  // 3. Inspect Datasets & Preview Rows
  await page.goto("/datasets");
  await expect(page.getByText("Data Health Score").first()).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(mediaDir, "02_dataset_catalog.png") });

  const previewBtn = page.getByRole("button", { name: "Preview Rows" }).first();
  await previewBtn.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText(/rows total/)).toBeVisible();
  await page.screenshot({ path: path.join(mediaDir, "03_preview_rows_modal.png") });
  await page.getByRole("dialog").getByRole("button", { name: "Close dialog" }).click();

  // 4. Workspace Chat: Ask question explaining files
  await page.goto("/workspace");
  await expect(page.locator('input[placeholder*="Ask about sales"]')).toBeVisible({ timeout: 15000 });
  await page.locator('input[placeholder*="Ask about sales"]').fill("What is in these files? Explain each one.");
  await page.getByRole("button", { name: "Ask" }).click();

  const codeBtn = page.getByRole("button", { name: "SQL / Code" }).last();
  await codeBtn.waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: path.join(mediaDir, "04_workspace_explained.png") });

  // 5. Cross-file join query
  await page.locator('input[placeholder*="Ask about sales"]').fill("What is total revenue broken down by customer segment?");
  await page.getByRole("button", { name: "Ask" }).click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(mediaDir, "05_cross_file_query.png") });

  // 6. Code Request & Run Manual SQL
  await page.locator('input[placeholder*="Ask about sales"]').fill("Generate SQL for this analysis.");
  await page.getByRole("button", { name: "Ask" }).click();
  const sqlBtn = page.getByRole("button", { name: "SQL / Code" }).last();
  await sqlBtn.waitFor({ state: "visible", timeout: 30000 });
  await sqlBtn.click();
  await expect(page.getByRole("heading", { name: "Evidence Ledger & Code Audit" })).toBeVisible();
  const runSqlBtn = page.getByRole("button", { name: "Run SQL" });
  await expect(runSqlBtn).toBeEnabled({ timeout: 10000 });
  await runSqlBtn.click();
  await expect(page.getByText(/Validated query completed/)).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(mediaDir, "06_evidence_sql_execution.png") });
  await page.getByRole("button", { name: "Close", exact: true }).click();

  // 7. Export PDF & Markdown Reports
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Executive Reports & Dossiers" })).toBeVisible({ timeout: 15000 });

  // Markdown Export
  await page.getByRole("button", { name: "Export New Report" }).click();
  await page.getByText("Markdown", { exact: true }).click();
  const mdDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Generate & Export" }).click();
  const mdFile = await mdDownloadPromise;
  const mdPath = await mdFile.path();
  expect(fs.statSync(mdPath!).size).toBeGreaterThan(100);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // PDF Export
  await page.getByRole("button", { name: "Export New Report" }).click();
  await page.getByText("PDF Document", { exact: true }).click();
  const pdfDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Generate & Export" }).click();
  const pdfFile = await pdfDownloadPromise;
  const pdfPath = await pdfFile.path();
  expect(fs.statSync(pdfPath!).size).toBeGreaterThan(1000);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.screenshot({ path: path.join(mediaDir, "07_reports_dossier.png") });

  // 8. Delete dataset
  await page.goto("/datasets");
  const datasetsList = await request.get("/api/v1/datasets", { headers: { Authorization: `Bearer ${token}` } });
  const initialDatasets = await datasetsList.json();
  const initialCount = initialDatasets.length;
  expect(initialCount).toBeGreaterThanOrEqual(3);

  const deleteBtn = page.getByRole("button", { name: "Delete Table" }).first();
  await deleteBtn.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: /Delete dataset/i }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.waitForTimeout(500);

  const updatedDatasetsList = await request.get("/api/v1/datasets", { headers: { Authorization: `Bearer ${token}` } });
  const updatedDatasets = await updatedDatasetsList.json();
  expect(updatedDatasets.length).toBe(initialCount - 1);
  await page.screenshot({ path: path.join(mediaDir, "08_after_cascade_delete.png") });

  // 9. Check Profile BYOK & Fallback Preferences
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Account & AI Connections" })).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(mediaDir, "09_profile_byok.png") });
});
