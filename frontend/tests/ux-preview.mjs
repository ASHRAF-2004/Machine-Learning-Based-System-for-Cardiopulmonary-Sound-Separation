import { chromium } from "playwright-core";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";

const base = process.env.STETHOFUSE_UX_URL || "http://127.0.0.1:4193";
if (!["127.0.0.1", "localhost", "[::1]"].includes(new URL(base).hostname))
  throw new Error("UX checks are local-only.");
const out = path.resolve(import.meta.dirname, "../output/playwright/ux-review");
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || "/usr/bin/google-chrome",
  headless: true,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
});
const errors = [],
  requests = [],
  results = [];
// Isolated test instrumentation observes native objects, preserving their behavior.
await context.addInitScript(() => {
  const state = (window.__uxEvidence = {
    contexts: [],
    gains: [],
    compressors: [],
    urls: [],
    revoked: [],
  });
  const Audio = window.AudioContext;
  window.AudioContext = class extends Audio {
    constructor(...args) {
      super(...args);
      state.contexts.push(this);
    }
    createGain() {
      const value = super.createGain();
      state.gains.push(value);
      return value;
    }
    createDynamicsCompressor() {
      const value = super.createDynamicsCompressor();
      state.compressors.push(value);
      return value;
    }
  };
  const create = URL.createObjectURL.bind(URL),
    revoke = URL.revokeObjectURL.bind(URL);
  URL.createObjectURL = (blob) => {
    const url = create(blob);
    state.urls.push(url);
    return url;
  };
  URL.revokeObjectURL = (url) => {
    state.revoked.push(url);
    revoke(url);
  };
});
const page = await context.newPage();
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) => requests.push(request.url()));
async function go(screen, query = "") {
  await page.goto(`${base}/ux-preview.html${query}#${screen}`);
  await page.getByRole("heading", { level: 1 }).waitFor();
  await page.evaluate(() => document.fonts.ready);
}
async function group(name, execute) {
  try {
    const detail = await execute();
    results.push({ name, status: "PASS", detail });
    console.log(`PASS ${name}`);
  } catch (error) {
    results.push({ name, status: "FAIL", detail: error.stack });
    console.error(`FAIL ${name}: ${error.message}`);
  }
}
try {
  await group(
    "Authenticated shell logo leads to Overview; lifecycle destinations consolidated",
    async () => {
      await go("library");
      await page
        .getByRole("link", { name: "StethoFuse Overview", exact: true })
        .click();
      await page
        .getByRole("heading", { name: "Good morning, Ashraf." })
        .waitFor();
      assert.equal(
        await page
          .getByRole("navigation", { name: "Main navigation" })
          .getByRole("link")
          .count(),
        2,
      );
      assert.equal(
        await page.getByText("Processing history", { exact: true }).count(),
        0,
      );
    },
  );
  await group(
    "Pine-eye owl follows pointer across sidebar and page, not only its hero",
    async () => {
      await page.waitForFunction(
        () =>
          document.querySelector(".sf-owl")?.dataset.renderer ===
          "approved-connected-neck",
        null,
        { timeout: 30000 },
      );
      await page.mouse.move(35, 550);
      await page.waitForFunction(
        () =>
          Number(document.querySelector(".sf-owl")?.dataset.targetYaw) < -10,
      );
      const left = await page.locator(".sf-owl").evaluate((el) => ({
        yaw: Number(el.dataset.targetYaw),
        pitch: Number(el.dataset.targetPitch),
        eye: el.dataset.eyeColour,
        scope: el.dataset.pointerScope,
      }));
      await page.mouse.move(1410, 610);
      await page.waitForFunction(
        () => Number(document.querySelector(".sf-owl")?.dataset.targetYaw) > 0,
      );
      const right = await page.locator(".sf-owl").evaluate((el) => ({
        yaw: Number(el.dataset.targetYaw),
        pitch: Number(el.dataset.targetPitch),
      }));
      assert.equal(left.eye, "pine-green");
      assert.equal(left.scope, "page");
      assert(right.yaw > left.yaw);
      return { left, right };
    },
  );
  await group(
    "Automatic media loading and actual finite waveform/STFT measurements",
    async () => {
      await go("recording");
      await page.waitForFunction(
        () =>
          document.querySelectorAll('[data-media-state="ready"]').length === 3,
      );
      assert.equal(
        await page.getByText("Load authorized file", { exact: true }).count(),
        0,
      );
      const signal = await page.evaluate(async () => {
        const { fixtureMedia } = await import("/src/ux-preview/fixtures.ts");
        const { decodeWav, measureSignal, spectrogram } = await import(
          "/src/ux-preview/signal.ts"
        );
        const decoded = await decodeWav(await fixtureMedia.media("original"));
        const metrics = measureSignal(decoded),
          spectrum = spectrogram(decoded);
        const tone = {
          samples: Float32Array.from({ length: 4000 }, (_, i) =>
            Math.sin((2 * Math.PI * 125 * i) / 4000),
          ),
          rate: 4000,
          channels: 1,
          duration: 1,
        };
        return {
          samples: decoded.samples.length,
          rate: decoded.rate,
          duration: decoded.duration,
          finite: decoded.samples.every(Number.isFinite),
          metrics,
          columns: spectrum.length,
          bins: spectrum[0].length,
          toneDb: spectrogram(tone)[0][8],
        };
      });
      assert.equal(signal.samples, 60000);
      assert.equal(signal.rate, 4000);
      assert(signal.finite);
      assert.equal(signal.bins, 129);
      assert.equal(signal.columns, 180);
      assert(Math.abs(signal.toneDb) < 0.001);
      assert(
        Object.values(signal.metrics).every(
          (value) => typeof value !== "number" || Number.isFinite(value),
        ),
      );
      return signal;
    },
  );
  await group(
    "200% playback uses GainNode 2 and compressor; single active source and keyboard seek",
    async () => {
      const slider = page.getByRole("slider", {
        name: "Original playback gain",
        exact: true,
      });
      await slider.focus();
      await slider.press("End");
      await page
        .getByRole("button", { name: "Play Original", exact: true })
        .click();
      await page.waitForFunction(
        () => window.__uxEvidence.gains[0]?.gain.value > 1.99,
      );
      const actual = await page.evaluate(() => {
        const e = window.__uxEvidence;
        return {
          gain: e.gains[0].gain.value,
          contexts: e.contexts.length,
          threshold: e.compressors[0].threshold.value,
          ratio: e.compressors[0].ratio.value,
        };
      });
      assert.equal(actual.contexts, 1);
      assert.equal(actual.threshold, -3);
      assert.equal(actual.ratio, 20);
      await page
        .getByRole("button", { name: "Play Heart", exact: true })
        .click();
      assert.equal(
        await page
          .getByRole("button", { name: "Pause Original", exact: true })
          .count(),
        0,
      );
      const seek = page.getByRole("slider", {
        name: "Seek Heart",
        exact: true,
      });
      await seek.focus();
      await seek.press("ArrowRight");
      assert(Number(await seek.inputValue()) > 0);
      await page
        .getByRole("button", { name: "Pause Heart", exact: true })
        .click();
      return actual;
    },
  );
  await group(
    "Blob URLs revoked and audio context closed on navigation",
    async () => {
      await page
        .getByRole("link", { name: "StethoFuse Overview", exact: true })
        .click();
      await page.waitForFunction(
        () =>
          window.__uxEvidence.revoked.length >= 3 &&
          window.__uxEvidence.contexts[0]?.state === "closed",
      );
      return await page.evaluate(() => ({
        allocated: window.__uxEvidence.urls.length,
        revoked: window.__uxEvidence.revoked.length,
      }));
    },
  );
  await group(
    "Frost/Midnight/System and playback preference survive reload",
    async () => {
      await page
        .getByRole("button", { name: "Switch to Midnight theme" })
        .click();
      await page.waitForFunction(
        () => document.documentElement.dataset.theme === "midnight",
      );
      await page.reload();
      await page.getByRole("heading", { level: 1 }).waitFor();
      assert.equal(
        await page.locator("html").getAttribute("data-theme"),
        "midnight",
      );
      await go("settings");
      await page
        .getByRole("button", { name: "System Follow your device", exact: true })
        .click();
      await page.emulateMedia({ colorScheme: "dark" });
      await page.waitForFunction(
        () => document.documentElement.dataset.theme === "midnight",
      );
      await page.emulateMedia({ colorScheme: "light" });
      await page.waitForFunction(
        () => document.documentElement.dataset.theme === "frost",
      );
      await go("recording");
      assert.equal(
        await page
          .getByRole("slider", { name: "Original playback gain" })
          .inputValue(),
        "200",
      );
    },
  );
  await group(
    "403 and 401 media errors remain denied/expired, without demo fallback",
    async () => {
      for (const state of ["denied", "expired"]) {
        await go("recording", `?mediaState=${state}`);
        const heart = page.locator(".sf-player--heart");
        await heart.locator('[role="alert"]').waitFor();
        assert.equal(
          await heart.getByRole("button", { name: "Play Heart" }).count(),
          0,
        );
        assert.equal(await heart.locator('a[href^="blob:"]').count(), 0);
        assert(
          (await heart.innerText()).includes(
            state === "denied"
              ? "do not currently have access"
              : "Sign in again",
          ),
        );
      }
    },
  );
  await group(
    "Desktop/tablet/mobile overflow and mobile source controls",
    async () => {
      for (const width of [1440, 1024, 390]) {
        await page.setViewportSize({
          width,
          height: width === 390 ? 844 : 900,
        });
        for (const screen of width === 390
          ? ["overview", "recording"]
          : ["overview", "library", "recording", "settings"]) {
          await go(screen);
          assert(
            await page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth + 1,
            ),
            `${screen} overflow at ${width}`,
          );
        }
      }
      await page
        .getByRole("group", { name: "Audio source", exact: true })
        .getByRole("button", { name: "Heart", exact: true })
        .click();
      assert(
        await page.getByRole("button", { name: "Play Heart" }).isVisible(),
      );
      assert(
        !(await page
          .getByRole("button", { name: "Play Original" })
          .isVisible()),
      );
      const play = await page
        .getByRole("button", { name: "Play Heart" })
        .boundingBox();
      assert(play.width >= 44 && play.height >= 44);
      await page
        .getByRole("button", { name: "Open navigation", exact: true })
        .click();
      await page.getByRole("dialog").waitFor();
      await page.keyboard.press("Escape");
      assert.equal(await page.getByRole("dialog").count(), 0);
    },
  );
  await group("Keyboard focus and modal focus return", async () => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await go("recording");
    await page.getByRole("button", { name: "Share", exact: true }).focus();
    await page.keyboard.press("Enter");
    assert(await page.getByRole("dialog").isVisible());
    await page.keyboard.press("Escape");
    assert(
      await page
        .getByRole("button", { name: "Share", exact: true })
        .evaluate((el) => el === document.activeElement),
    );
    const focus = await page
      .getByRole("button", { name: "Share", exact: true })
      .evaluate((el) => ({
        style: getComputedStyle(el).outlineStyle,
        width: getComputedStyle(el).outlineWidth,
      }));
    assert.equal(focus.style, "solid");
    assert.equal(focus.width, "2px");
  });
  await group(
    "Preview identity persists one handle change without replacing internal security identity",
    async () => {
      await go("settings");
      await page.getByLabel("Display name", { exact: true }).fill("Ashraf A.");
      await page
        .getByLabel("Public handle", { exact: true })
        .fill("frostcedar");
      await page
        .getByRole("button", { name: "Save profile", exact: true })
        .click();
      assert(await page.getByLabel("Public handle").isDisabled());
      await page.reload();
      assert.equal(
        await page.getByLabel("Public handle").inputValue(),
        "frostcedar",
      );
      assert.equal(
        await page.getByLabel("Display name").inputValue(),
        "Ashraf A.",
      );
      assert(
        (await page.locator(".sf-sidebar-account").innerText()).includes(
          "@frostcedar",
        ),
      );
    },
  );
  await group(
    "Reduced motion skips owl renderer loads and transform motion",
    async () => {
      const reduced = await browser.newContext({
          viewport: { width: 1440, height: 900 },
          reducedMotion: "reduce",
        }),
        rp = await reduced.newPage(),
        seen = [];
      rp.on("request", (r) => seen.push(r.url()));
      await rp.goto(`${base}/ux-preview.html#overview`);
      await rp.getByRole("heading", { level: 1 }).waitFor();
      const owl = rp.locator(".sf-owl img");
      await owl.waitFor();
      await rp.getByRole("button", { name: "New recording" }).hover();
      assert.equal(
        await rp
          .getByRole("button", { name: "New recording" })
          .evaluate((el) => getComputedStyle(el).transform),
        "none",
      );
      assert.equal(
        seen.filter((url) => new URL(url).pathname.startsWith("/assets/owl/"))
          .length,
        0,
      );
      await reduced.close();
    },
  );
  await group(
    "No unexpected console errors or external/production requests",
    async () => {
      assert.deepEqual(errors, []);
      const external = requests.filter(
        (url) =>
          url.startsWith("http") &&
          new URL(url).origin !== new URL(base).origin,
      );
      assert.deepEqual(external, []);
      return {
        requests: requests.length,
        externalRequests: external.length,
        consoleErrors: errors.length,
      };
    },
  );
} finally {
  await fs.writeFile(
    path.join(out, "focused-checks.json"),
    JSON.stringify(
      {
        testedAt: new Date().toISOString(),
        browser: await browser.version(),
        base,
        scope:
          "Isolated local generated-fixture UX checks, NOT a live authorization/security qualification.",
        results,
        errors,
      },
      null,
      2,
    ),
  );
  await browser.close();
}
if (results.some((result) => result.status === "FAIL")) process.exitCode = 1;
