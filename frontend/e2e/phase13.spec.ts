import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("Phase 13 live data flow: scopes, report preview/download, paginated preview, and delete", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(180000);
  const email = `phase13_${Date.now()}@example.com`;
  const registration = await request.post("/api/v1/auth/register", {
    data: { email, password: "Password123!", full_name: "Phase 13 Audit" },
  });
  expect(registration.ok()).toBeTruthy();
  const login = await request.post("/api/v1/auth/login", {
    data: { email, password: "Password123!" },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token: token } = await login.json();
  await page.addInitScript((value: string) => localStorage.setItem("lumen_access_token", value), token);

  const root = path.resolve(process.cwd(), "../sample_data");
  await page.goto("/datasets");
  await page.locator('input[type="file"]').setInputFiles(
    ["sales.csv", "customers.csv", "products.csv"].map((name) => path.join(root, name)),
  );
  await expect(page.getByText("Data Health Score").first()).toBeVisible({ timeout: 20000 });
  const datasetsResponse = await request.get("/api/v1/datasets", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const datasets = await datasetsResponse.json();
  expect(datasets).toHaveLength(3);

  await page.goto("/dashboards");
  await expect(page.getByText("Files analyzed")).toBeVisible({ timeout: 15000 });
  await expect(page.locator("text=3.00").first()).toBeVisible();
  await page.getByRole("button", { name: datasets[0].name }).click();
  await expect(page.getByText(`Rows in ${datasets[0].table_name}`)).toBeVisible();

  const dashboardDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export PDF" }).click();
  const dashboardFile = await dashboardDownload;
  const dashboardPath = await dashboardFile.path();
  expect(dashboardPath).toBeTruthy();
  expect(fs.statSync(dashboardPath!).size).toBeGreaterThan(1000);
  expect(fs.readFileSync(dashboardPath!).subarray(0, 5).toString()).toBe("%PDF-");

  const initialSession = await request.post("/api/v1/chat/sessions", {
    headers: { Authorization: `Bearer ${token}` },
    data: { title: "SQL Run Audit" },
  });
  expect(initialSession.status()).toBe(201);
  const sessionId = (await initialSession.json()).id as string;
  const overviewResponse = await request.post(`/api/v1/chat/sessions/${sessionId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { content: "What is in these 3 files? Explain each one." },
  });
  const overviewText = await overviewResponse.text();
  expect(overviewText).toContain("sales");
  expect(overviewText).toContain("customers");
  expect(overviewText).toContain("products");

  const artifactResponse = await request.get("/api/v1/reports", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(artifactResponse.ok()).toBeTruthy();
  const artifacts = await artifactResponse.json();
  expect(artifacts.length).toBeGreaterThan(0);
  await page.goto("/reports");
  await expect(page.getByRole("button", { name: "Preview" }).first()).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: "Preview" }).first().click();
  await expect(page.locator("iframe[title]")).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  const reportDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).first().click();
  const reportFile = await reportDownload;
  expect(fs.statSync((await reportFile.path())!).size).toBeGreaterThan(1000);

  await page.getByRole("button", { name: "Export New Report" }).click();
  await page.getByRole("button", { name: "Markdown" }).click();
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Generate & Export" }).click();
  const markdownFile = await markdownDownload;
  const markdownText = fs.readFileSync((await markdownFile.path())!, "utf-8");
  expect(markdownText).toContain("# ");
  expect(markdownText).toContain("Evidence Ledger");

  const sessionReady = page.waitForResponse((response) =>
    response.url().includes("/api/v1/chat/sessions") && response.request().method() === "GET" && response.status() === 200,
  );
  await page.goto("/workspace");
  await sessionReady;
  await expect(page.getByText("SQL Run Audit")).toBeVisible();
  await page.locator('input[placeholder*="Ask about sales"]').fill("Generate SQL for this analysis.");
  await page.getByRole("button", { name: "Ask" }).click();
  await page.getByRole("button", { name: "SQL / Code" }).last().waitFor({ state: "visible", timeout: 60000 });
  await page.getByRole("button", { name: "SQL / Code" }).last().click();
  await expect(page.getByRole("heading", { name: "Evidence Ledger & Code Audit" })).toBeVisible();
  await page.getByRole("button", { name: "Run SQL" }).click();
  await expect(page.getByText(/Validated query completed/)).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.goto("/datasets");
  await expect(page.getByRole("button", { name: "Preview Rows" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Preview Rows" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("button", { name: "Next" })).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Close dialog" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const target = datasets[0];
  const deleteButton = page.getByRole("button", { name: "Delete Table" }).first();
  await deleteButton.click();
  await expect(page.getByText(/delete/i).last()).toBeVisible();
  await page.getByRole("button", { name: /Delete dataset/i }).click();
  await expect(page.getByText(target.name, { exact: false })).toHaveCount(0);
  const remaining = await request.get("/api/v1/datasets", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(await remaining.json()).toHaveLength(2);

  const answer = await request.post(`/api/v1/chat/sessions/${sessionId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { content: "What is in these files? Explain each file." },
  });
  const answerText = await answer.text();
  expect(answerText).not.toContain(target.table_name);
  expect(answerText).not.toContain(target.name);

  await page.screenshot({ path: testInfo.outputPath("phase13-after-delete.png") });
});
