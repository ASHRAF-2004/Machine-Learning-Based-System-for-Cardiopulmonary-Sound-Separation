import { chromium } from "playwright-core";
import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

// Capture the local design proof, never a live account or production recording.
const base = process.env.STETHOFUSE_UX_URL || "http://127.0.0.1:4193";
if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(base).hostname))
  throw new Error("UX preview captures are local-only.");
const revision = process.env.STETHOFUSE_UX_REVISION || "";
if (revision && !/^[a-z0-9-]{1,40}$/.test(revision))
  throw new Error("UX evidence revision must be a simple directory name.");
const out = path.resolve(import.meta.dirname, "../output/playwright/ux-review", revision);
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || "/usr/bin/google-chrome",
  headless: true,
});
const screenshots = [];
async function capture(file, screen, theme = "frost", mobile = false, section, { gain, tablet = false } = {}) {
  const viewport = mobile
    ? { width: 390, height: 844 }
    : tablet ? { width: 900, height: 900 }
    : { width: 1440, height: 900 };
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: screen === "overview" ? 3 : 1,
    colorScheme: theme === "midnight" ? "dark" : "light",
    isMobile: mobile,
    hasTouch: mobile,
  });
  await context.addInitScript((preference) => {
    localStorage.setItem("sf-design-theme", preference);
    localStorage.setItem("sf-design-gain", "100");
  }, theme);
  const page = await context.newPage();
  await page.goto(`${base}/ux-preview.html#${screen}`);
  await page.getByRole("heading", { level: 1 }).waitFor();
  await page.evaluate(() => document.fonts.ready);
  if (screen === "recording") {
    await page.waitForFunction(
      () =>
        document.querySelectorAll('[data-media-state="ready"]').length === 3,
    );
    if (gain !== undefined) {
      const slider = page.getByRole("slider", { name: "Original playback volume", exact: true });
      await slider.focus();
      await slider.press("Home");
      for (let step = 0; step < gain / 5; step++) await slider.press("ArrowRight");
      if (await slider.inputValue() !== String(gain)) throw new Error("Requested boost state did not render");
    }
  }
  if (screen === "overview" && !mobile) {
    await page.waitForFunction(
      () =>
        document.querySelector(".sf-owl")?.dataset.renderer ===
        "approved-connected-neck",
      null,
      { timeout: 30000 },
    );
    const owl = await page.locator(".sf-owl").boundingBox();
    await page.mouse.move(
      owl.x + owl.width * 0.428,
      owl.y + owl.height * 0.192,
    );
    await page.waitForFunction(
      () =>
        Math.abs(Number(document.querySelector(".sf-owl")?.dataset.yaw)) < 0.01,
    );
  }
  if (section)
    await page
      .getByRole("navigation", { name: "Settings sections" })
      .getByRole("button", { name: section, exact: true })
      .click();
  await page.screenshot({
    path: path.join(out, file),
    animations: "disabled",
    scale: "css",
  });
  if (screen === "overview" && !tablet) {
    const closeup = mobile ? "owl-perch-mobile-closeup.png" : "owl-perch-desktop-closeup.png";
    await page.locator(".sf-greeting-art").screenshot({
      path: path.join(out, closeup),
      animations: "disabled",
      scale: "device",
    });
    screenshots.push({ file: closeup, viewport, theme, screen, kind: "owl-contact-closeup", sha256: createHash("sha256").update(await fs.readFile(path.join(out, closeup))).digest("hex") });
  }
  const bytes = await fs.readFile(path.join(out, file));
  screenshots.push({
    file,
    viewport,
    theme,
    screen,
    ...(section ? { section } : {}),
    ...(gain !== undefined ? { playbackVolumePercent: gain, setThrough: "native slider keyboard input" } : {}),
    sha256: createHash("sha256").update(bytes).digest("hex"),
  });
  await context.close();
  console.log(file);
}
try {
  await capture("01-overview-light-desktop.png", "overview");
  await capture("02-library-light-desktop.png", "library");
  await capture("03-recording-detail-light-desktop.png", "recording");
  await capture("04-profile-settings-light-desktop.png", "settings");
  await capture(
    "05-recording-detail-midnight-desktop.png",
    "recording",
    "midnight",
  );
  await capture("06-overview-mobile.png", "overview", "frost", true);
  await capture("07-recording-detail-mobile.png", "recording", "frost", true);
  await capture(
    "08-profile-privacy-desktop.png",
    "settings",
    "frost",
    false,
    "Privacy & data",
  );
  await capture("09-recording-detail-boost150-desktop.png", "recording", "frost", false, undefined, { gain: 150 });
  await capture("10-overview-tablet.png", "overview", "frost", false, undefined, { tablet: true });
  await capture("11-recording-detail-boost200-mobile.png", "recording", "frost", true, undefined, { gain: 200 });
  await fs.writeFile(
    path.join(out, "preview-index.json"),
    JSON.stringify(
      { generatedAt: new Date().toISOString(), base, screenshots },
      null,
      2,
    ) + "\n",
  );
} finally {
  await browser.close();
}
