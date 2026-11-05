/**
 * Automated Screenshot Capture for Lumen documentation.
 * Uses Playwright to render multi-viewport responsive previews and saves to docs/media/screenshots.
 */
import { execSync } from "child_process";

console.log("Running Playwright multi-viewport and multi-screen screenshot capture...");
execSync("npx playwright test e2e/generate_demo_and_media.spec.ts", {
  cwd: "./frontend",
  stdio: "inherit",
});
console.log("Screenshots captured successfully in docs/media/screenshots/");
