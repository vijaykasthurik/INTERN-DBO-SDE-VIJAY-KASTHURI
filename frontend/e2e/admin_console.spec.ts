import { test, expect } from "@playwright/test";

test("admin console full authentication, navigation, query execution, and sign out", async ({ page, request }) => {
  // Ensure admin user exists by calling backend directly if needed
  const adminEmail = "admin@lumen.internal";
  const adminPassword = "AdminSecretPass2026!#";

  // Check login API directly to confirm credentials
  const preCheck = await request.post("/api/v1/admin/login", {
    data: { email: adminEmail, password: adminPassword },
  });
  expect(preCheck.status()).toBe(200);

  // 1. Visit hidden route /admin2005
  await page.goto("/admin2005");
  await expect(page).toHaveURL(/admin2005/);

  // Verify meta robots tag is present
  const robotsMeta = page.locator('meta[name="robots"]');
  await expect(robotsMeta).toHaveAttribute("content", "noindex, nofollow");

  // 2. Perform Administrative Login
  await expect(page.getByText("Lumen Administration")).toBeVisible();
  await page.fill('input[type="email"]', adminEmail);
  await page.fill('input[type="password"]', adminPassword);
  await page.click('button[type="submit"]');

  // 3. Confirm Dashboard Shell Loads
  await expect(page.getByText("ADMIN CONSOLE - CONFIDENTIAL")).toBeVisible();
  await expect(page.getByText("Active Users (24h)")).toBeVisible();

  // 4. Navigate Tabs: Users
  await page.click('button:has-text("Users")');
  await expect(page.getByText("Total Accounts:")).toBeVisible();
  await expect(page.getByText(adminEmail)).toBeVisible();

  // 5. Navigate Tabs: Database & SQL Console
  await page.click('button:has-text("Database")');
  await page.click('button:has-text("SQL Console")');

  // Fill and run a safe SELECT query
  const queryBox = page.locator("textarea");
  await queryBox.fill("SELECT 1 AS probe_col;");
  await page.click('button:has-text("Execute Query")');

  // Verify query result renders in grid
  await expect(page.getByText("probe_col")).toBeVisible();
  await expect(page.getByText("1").first()).toBeVisible();

  // 6. Navigate Tabs: Operations & Settings
  await page.click('button:has-text("Operations")');
  await expect(page.getByText("Operational Feature Flags & Guardrails")).toBeVisible();
  await expect(page.getByText("Allow Public Registration")).toBeVisible();

  // 7. Navigate Tabs: Audit Log
  await page.click('button:has-text("Audit")');
  await expect(page.getByText("Showing recent 50 immutable audit records")).toBeVisible();

  // 8. Sign Out and verify session purge
  await page.click('button:has-text("Sign Out")');
  await expect(page).toHaveURL(/\//);

  // Verify token is cleared from sessionStorage
  const tokenAfterSignOut = await page.evaluate(() => sessionStorage.getItem("lumen_admin_token"));
  expect(tokenAfterSignOut).toBeNull();
});
