import { test, expect } from "@playwright/test";

test.describe("Lumen BYOK AI Provider & Fallback E2E Flow", () => {
  test("Navbar AI chip, Connect AI modal, and Profile page management", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });

    // 1. Register & login
    await page.goto("/auth");
    await page.waitForLoadState("networkidle");

    const email = `byok_e2e_${Date.now()}@example.com`;
    const password = "Password123!";

    await page.click("text=Create Account");
    await page.fill('input[placeholder="Jane Doe"]', "E2E BYOK Reviewer");
    await page.fill('input[type="email"]', email);
    await page.fill('input[placeholder="Min. 8 characters"]', password);
    await page.click('button[type="submit"]:has-text("Create Account")');

    // Wait until redirected to workspace
    await expect(page).toHaveURL(/.*workspace/);

    // 2. Verify AI Status Chip in floating navbar
    const aiChip = page.locator('button:has-text("Shared AI")');
    await expect(aiChip).toBeVisible();

    // 3. Click AI chip -> Opens 'Connect your AI' modal
    await aiChip.click();
    await expect(page.locator("h3:has-text('Connect your AI')")).toBeVisible();
    await expect(page.locator("text=Encrypted at rest with AES-256-GCM")).toBeVisible();

    // 4. Test provider selection in modal (e.g. click Groq)
    await page.click('button:has-text("Groq")');
    await expect(page.locator('input[placeholder*="gsk_"]')).toBeVisible();

    // 5. Close modal
    await page.click('button[aria-label="Close dialog"]');
    await expect(page.locator("h3:has-text('Connect your AI')")).not.toBeVisible();

    // 6. Navigate to /profile
    await page.goto("/profile");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("h1:has-text('Account & AI Connections')")).toBeVisible();
    await expect(page.locator("text=Shared Server Model Pool (Demo Mode)")).toBeVisible();
    await expect(page.locator("text=Groq 7-Key Pool")).toBeVisible();

    // 7. Verify 'Connect your AI Key' button opens popup from Profile
    await page.click('button:has-text("Connect your AI Key")');
    await expect(page.locator("h3:has-text('Connect your AI')")).toBeVisible();
    await page.click('button:has-text("Cancel")');
    await expect(page.locator("h3:has-text('Connect your AI')")).not.toBeVisible();
  });
});
