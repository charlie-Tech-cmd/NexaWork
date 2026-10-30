// Local QA: PLAYWRIGHT_MODULE and AXE_PATH may point to separately installed test tools.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || undefined,
    headless: true,
  });
  const base = process.env.BASE_URL || "http://127.0.0.1:3000";
  const output =
    process.env.QA_OUTPUT_DIR ||
    path.join(require("node:os").tmpdir(), "nexawork-landing-qa");
  fs.mkdirSync(output, { recursive: true });
  const results = [];
  try {
    for (const width of [320, 390, 430, 768, 1280, 1440]) {
      const page = await browser.newPage({
        viewport: { width, height: 1000 },
        reducedMotion: "reduce",
      });
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      await page.goto(base);
      await page
        .locator(".hero-conference img")
        .evaluate((image) => image.decode());
      assert.equal(await page.locator("h1").count(), 1);
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
        `overflow at ${width}`,
      );
      assert.ok(
        (await page
          .locator(".landing-section-heading h2 span")
          .first()
          .evaluate((el) => parseFloat(getComputedStyle(el).fontSize))) >= 32,
        "heading typography survives workspace CSS",
      );
      for (const href of ["#product", "#features", "#about", "#contact"])
        assert.equal(await page.locator(href).count(), 1);
      const messages = page.getByRole("tab", { name: "Messages", exact: true });
      const files = page.getByRole("tab", { name: "Files 3", exact: true });
      await messages.focus();
      await page.keyboard.press("ArrowRight");
      assert.equal(await files.getAttribute("aria-selected"), "true");
      assert.equal(
        await files.evaluate((el) => el === document.activeElement),
        true,
      );
      assert.equal(await page.getByRole("tabpanel").count(), 1);
      assert.equal(
        await page
          .getByRole("heading", { name: "Shared in this conversation" })
          .isVisible(),
        true,
      );
      await page.keyboard.press("Home");
      assert.equal(await messages.getAttribute("aria-selected"), "true");
      await page.keyboard.press("End");
      assert.equal(await files.getAttribute("aria-selected"), "true");
      await page.keyboard.press("ArrowRight");
      assert.equal(await messages.getAttribute("aria-selected"), "true");
      await files.click();
      assert.equal(
        await page.locator("#preview-panel-files").isVisible(),
        true,
      );
      await messages.click();
      if (width <= 800) {
        const menu = page.getByRole("button", { name: "Menu" });
        await menu.click();
        assert.equal(
          await page.locator("#landing-navigation").isVisible(),
          true,
        );
        await page.keyboard.press("Escape");
        assert.equal(await menu.getAttribute("aria-expanded"), "false");
        assert.equal(
          await menu.evaluate((el) => el === document.activeElement),
          true,
        );
        await menu.click();
        await page
          .getByRole("navigation", { name: "Main navigation", exact: true })
          .getByRole("link", { name: "Product", exact: true })
          .click();
        assert.equal(await menu.getAttribute("aria-expanded"), "false");
      }
      if (process.env.AXE_PATH && [390, 1440].includes(width)) {
        await page.addScriptTag({ path: process.env.AXE_PATH });
        const scan = await page.evaluate(
          async () =>
            (
              await axe.run(document.querySelector(".landing-page"), {
                runOnly: {
                  type: "tag",
                  values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
                },
              })
            ).violations,
        );
        fs.writeFileSync(
          path.join(output, `nexawork-axe-${width}.json`),
          JSON.stringify(scan, null, 2),
        );
        assert.deepEqual(
          scan.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
          [],
          `axe violations ${width}`,
        );
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      if ([390, 1440].includes(width)) {
        await page.screenshot({
          path: path.join(
            output,
            `nexawork-landing-${width === 390 ? "mobile" : "desktop"}.png`,
          ),
          fullPage: true,
        });
        await page.screenshot({
          path: path.join(output, `nexawork-landing-${width}-hero.png`),
        });
        await files.click();
        await page.locator(".workspace-demo").screenshot({
          path: path.join(output, `nexawork-files-preview-${width}.png`),
        });
      }
      assert.deepEqual(errors, [], `browser errors ${width}`);
      results.push({
        width,
        overflow: false,
        tabs: "PASS",
        navigation: "PASS",
        console: "PASS",
      });
      await page.close();
    }
    const page = await browser.newPage();
    await page.goto(base);
    await page.locator('.hero-actions a[href="/get-started"]').click();
    await page.locator("form").waitFor();
    assert.equal(new URL(page.url()).pathname, "/get-started");
    assert.equal(await page.locator("form").count(), 1);
    await page.goto(base);
    await page.locator(".landing-sign-in").click();
    await page.locator('input[type="password"]').waitFor();
    assert.equal(new URL(page.url()).pathname, "/sign-in");
    assert.equal(await page.locator('input[type="password"]').count(), 1);
    results.push({ authRoutes: "PASS (forms loaded, no account submitted)" });
    await page.route("**/images/conference-*.webp", (route) => route.abort());
    await page.goto(base);
    await page
      .getByRole("img", { name: "Conference illustration unavailable" })
      .waitFor();
    assert.equal(
      await page
        .getByRole("img", { name: "Conference illustration unavailable" })
        .isVisible(),
      true,
    );
    results.push({ imageFailure: "PASS" });
    fs.writeFileSync(
      path.join(output, "nexawork-landing-browser-results.json"),
      JSON.stringify(results, null, 2),
    );
    console.log(JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
