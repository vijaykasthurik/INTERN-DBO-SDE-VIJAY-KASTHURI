/**
 * Automated Playwright demo video recording for Lumen.
 * Captures query execution, evidence drawer spring-in, and dashboard generation.
 */
import { execSync } from "child_process";

console.log("Recording interactive product demo with Playwright...");
execSync("npx playwright test e2e/capture_all_media.spec.ts", {
  cwd: "./frontend",
  stdio: "inherit",
});
console.log("Interactive video captured and persisted in docs/media/demo/");
