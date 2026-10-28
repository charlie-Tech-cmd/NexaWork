import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { publicView, resetTokenFromSearch } from "../src/landing/content.ts";

test("public URLs resolve to distinct onboarding, login, and protected workspace views", () => {
  assert.equal(publicView("/"), "landing");
  assert.equal(publicView("/get-started"), "onboard");
  assert.equal(publicView("/sign-in"), "login");
  assert.equal(publicView("/workspace"), "workspace");
  assert.equal(publicView("/reset-password"), "reset");
  assert.equal(publicView("/reset-password/"), "reset");
});

test("reset token is extracted from the email link query string", () => {
  assert.equal(resetTokenFromSearch("?token=abc123"), "abc123");
  assert.equal(
    resetTokenFromSearch("?source=email&token=abc%2B123"),
    "abc+123",
  );
  assert.equal(resetTokenFromSearch("?source=email"), "");
  assert.equal(resetTokenFromSearch("?token=%20%20"), "");
});
test("trailing slashes are accepted without mistaking unrelated routes for auth", () => {
  assert.equal(publicView("/get-started/"), "onboard");
  assert.equal(publicView("/sign-in/"), "login");
  for (const path of [
    "/unknown",
    "/get-started-extra",
    "/privacy",
    "/terms",
    "https://example.test",
  ])
    assert.equal(publicView(path), "not-found");
});
test("responsive office assets are real JPEGs under the per-image budget", async () => {
  for (const name of ["team-office", "office-collaboration"]) {
    for (const width of [720, 1440]) {
      const path = new URL(
        `../public/images/${name}-${width}.jpg`,
        import.meta.url,
      );
      const bytes = await readFile(path);
      assert.equal(bytes[0], 0xff);
      assert.equal(bytes[1], 0xd8);
      assert.ok(
        (await stat(path)).size < 250_000,
        "Each optimized image must remain below 250 kB",
      );
    }
  }
});
