/**
 * Automated Screenshot Capture for Lumen documentation.
 * Uses Playwright to render multi-viewport responsive previews.
 */
import { execSync } from "child_process";

console.log("Running Playwright multi-viewport screenshot capture...");
execSync("npx playwright test e2e/smoke.spec.ts", {
  cwd: "./frontend",
  stdio: "inherit",
});
console.log("Screenshots captured successfully in docs/media/screenshots/");
