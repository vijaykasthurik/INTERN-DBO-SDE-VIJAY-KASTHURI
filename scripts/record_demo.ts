/**
 * Automated Playwright demo video recording for Lumen.
 * Captures query execution, evidence drawer spring-in, dashboard generation, and converts to MP4 & GIF.
 */
import { execSync } from "child_process";

console.log("Recording interactive product demo with Playwright...");
execSync("npx playwright test e2e/generate_demo_and_media.spec.ts", {
  cwd: "./frontend",
  stdio: "inherit",
});
console.log("Transcoding recorded video to docs/media/demo.mp4 and docs/media/demo.gif...");
execSync('ffmpeg -y -i "frontend/test-results/generate_demo_and_media-Ge-c2102-shots-and-interactive-video-chromium/video.webm" -c:v libx264 -pix_fmt yuv420p -preset fast -crf 23 -movflags +faststart "docs/media/demo.mp4"', { stdio: "inherit" });
execSync('ffmpeg -y -i "docs/media/demo.mp4" -vf "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" "docs/media/demo.gif"', { stdio: "inherit" });
execSync('copy /Y "docs\\media\\demo.mp4" "docs\\media\\demo\\lumen_demo.mp4"', { shell: "cmd.exe" });
execSync('copy /Y "docs\\media\\demo.gif" "docs\\media\\demo\\lumen_demo.gif"', { shell: "cmd.exe" });
console.log("Interactive video and GIF successfully generated.");
