import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import {
  ApiError,
  request,
  loginSession,
  records,
  structurePath,
  structurePayload,
} from "../src/api.ts";
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});
function respond(body: unknown, status = 200) {
  globalThis.fetch = async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
}
test("authenticated writes send bearer token and JSON without cookies", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "/api/v1/users");
    assert.equal(init?.method, "POST");
    assert.equal(init?.credentials, "omit");
    assert.equal(init?.redirect, "error");
    assert.equal(init?.cache, "no-store");
    assert.deepEqual(init?.headers, {
      Authorization: "Bearer test-token",
      "Content-Type": "application/json",
    });
    assert.deepEqual(JSON.parse(String(init?.body)), {
      full_name: "Test Person",
    });
    return new Response('{"id":1}');
  };
  assert.deepEqual(
    await request("/users", "test-token", "POST", { full_name: "Test Person" }),
    { id: 1 },
  );
});
test("403 remains a permission error", async () => {
  respond({ detail: "Permission denied" }, 403);
  await assert.rejects(
    request("/users", "token"),
    (error) =>
      error instanceof ApiError &&
      error.status === 403 &&
      error.message === "Permission denied",
  );
});
test("401 preserves status for session expiry handling", async () => {
  respond({}, 401);
  await assert.rejects(
    request("/users", "token"),
    (error) => error instanceof ApiError && error.status === 401,
  );
});
test("validation errors identify fields without exposing submitted values", async () => {
  respond(
    {
      detail: [
        {
          loc: ["body", "email"],
          msg: "Invalid email",
          input: "private-value",
        },
      ],
    },
    422,
  );
  await assert.rejects(request("/users"), { message: "email: Invalid email" });
});
test("server errors conceal exception details", async () => {
  respond({ detail: "database internal secret" }, 500);
  await assert.rejects(
    request("/users"),
    (error) => error instanceof ApiError && !error.message.includes("secret"),
  );
});
test("network failure offers recovery", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("fetch failed");
  };
  await assert.rejects(request("/users"), {
    message:
      "Could not reach your workspace. Check your connection and try again.",
  });
});
test("malformed successful responses are rejected", async () => {
  globalThis.fetch = async () => new Response("<html>proxy error</html>");
  await assert.rejects(request("/users"), {
    message: "The server returned an unreadable response.",
  });
  assert.throws(() => records([{ name: "missing id" }]));
  assert.throws(() => records({ items: [] }));
  assert.throws(() =>
    loginSession(
      { id: 1, email: "user@example.test", full_name: "Test" },
      "member",
    ),
  );
});
test("empty success responses are supported", async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 });
  assert.equal(await request("/roles/1", "token", "DELETE"), null);
});
test("hierarchy matches backend paths and team payload", () => {
  assert.equal(structurePath(0, 7), "/regions/organizations/7");
  assert.equal(structurePath(1, 8), "/branches/regions/8");
  assert.equal(structurePath(2, 9), "/departments/branches/9");
  assert.equal(structurePath(3, 10), "/teams/departments/10");
  assert.deepEqual(structurePayload(3, 10, { name: "Team", slug: "team" }), {
    name: "Team",
    slug: "team",
    department_id: 10,
  });
  assert.throws(() => structurePath(4, 1));
  assert.throws(() => structurePath(0, 0));
});
test("external URLs cannot receive credentials", async () => {
  await assert.rejects(request("https://example.test", "token"));
  await assert.rejects(request("//example.test", "token"));
});
