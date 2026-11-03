import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  createMessagingApi,
  mergeMessages,
  titleFor,
  checkFiles,
  type Message,
} from "../src/messaging-api.ts";
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});
const message = (id: number, body = "Hello"): Message => ({
  id,
  sender_id: 1,
  body,
  created_at: "2026-10-29T10:00:00Z",
  attachments: [],
  reply_to: null,
});
test("history pages merge without duplicates and update existing messages in ID order", () => {
  assert.deepEqual(
    mergeMessages(
      [message(4), message(2)],
      [message(1), message(4, "updated")],
    ).map((m) => [m.id, m.body]),
    [
      [1, "Hello"],
      [2, "Hello"],
      [4, "updated"],
    ],
  );
});
test("direct titles exclude the current member; groups use their name", () => {
  const c = {
    id: 1,
    name: null,
    conversation_type: "direct" as const,
    members: [
      { id: 1, full_name: "Me" },
      { id: 2, full_name: "Colleague" },
    ],
  };
  assert.equal(titleFor(c, 1), "Colleague");
  assert.equal(titleFor({ ...c, name: "Design" }, 1), "Design");
});
test("client file checks reject disabled, empty, oversized, unsupported and excessive files", () => {
  const p = {
    enabled: true,
    uploads_enabled: true,
    max_bytes: 10,
    max_attachments: 2,
    extensions: [".txt"],
  };
  checkFiles([new File(["hello"], "notes.txt")], p);
  for (const files of [
    [new File([], "empty.txt")],
    [new File(["12345678901"], "big.txt")],
    [new File(["a"], "run.exe")],
    Array.from({ length: 3 }, () => new File(["a"], "a.txt")),
  ])
    assert.throws(() => checkFiles(files, p));
  assert.throws(() => checkFiles([], { ...p, enabled: false }));
  assert.throws(() => checkFiles([], { ...p, uploads_enabled: false }));
});
test("conversation cursors are encoded and sent only to the fixed API route", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(
      url,
      "/api/v1/messaging/conversations/page?limit=30&cursor=a%2Fb%2Bc",
    );
    assert.equal(
      (init?.headers as Record<string, string>).Authorization,
      "Bearer private",
    );
    return new Response('{"items":[],"next_cursor":null}');
  };
  await createMessagingApi("private", () => {}).conversations("a/b+c");
});
test("uploads send raw binary with encoded filename, no cookies or redirects", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "/api/v1/messaging/conversations/7/attachments");
    assert.equal(init?.method, "POST");
    assert.ok(init?.body instanceof File);
    assert.equal(init?.credentials, "omit");
    assert.equal(init?.redirect, "error");
    assert.equal(
      (init?.headers as Record<string, string>)["X-Filename"],
      "team%20notes.txt",
    );
    return new Response('{"id":1}');
  };
  await createMessagingApi("token", () => {}).upload(
    7,
    new File(["hello"], "team notes.txt"),
    new AbortController().signal,
  );
});
test("file policy parses backend availability before exposing upload controls", async () => {
  const api = createMessagingApi("token", () => {});
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        enabled: true,
        uploads_enabled: false,
        max_bytes: 10,
        max_attachments: 2,
        extensions: [".txt"],
      }),
    );
  assert.deepEqual(await api.policy(), {
    enabled: true,
    uploads_enabled: false,
    max_bytes: 10,
    max_attachments: 2,
    extensions: [".txt"],
  });

  globalThis.fetch = async () => new Response("{}");
  await assert.rejects(api.policy(), /unexpected response/i);

  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        enabled: false,
        uploads_enabled: true,
        max_bytes: 10,
        max_attachments: 2,
        extensions: [".txt"],
      }),
    );
  await assert.rejects(api.policy(), /unexpected response/i);
});
test("retry sends keep the same client message identifier and attachment IDs", async () => {
  const sent: unknown[] = [];
  globalThis.fetch = async (_url, init) => {
    sent.push(JSON.parse(String(init?.body)));
    return new Response(JSON.stringify(message(5)));
  };
  const api = createMessagingApi("token", () => {}),
    key = "ca9102af-3447-4d3f-b49d-46aff61bd523";
  await api.send(1, "hello", [2, 3], key);
  await api.send(1, "hello", [2, 3], key);
  assert.deepEqual(sent[0], sent[1]);
  assert.deepEqual(sent[0], {
    body: "hello",
    attachment_ids: [2, 3],
    client_message_id: key,
  });
});
test("replies include their target and read receipts use conversation-scoped routes", async () => {
  const requests: { url: string; body: unknown }[] = [];
  globalThis.fetch = async (url, init) => {
    requests.push({
      url: String(url),
      body: init?.body ? JSON.parse(String(init.body)) : null,
    });
    if (String(url).endsWith("/messages/12"))
      return new Response(JSON.stringify(message(12)));
    if (String(url).endsWith("/read-state"))
      return new Response(
        JSON.stringify({ members: [{ user_id: 2, last_read_at: null }] }),
      );
    if (String(url).endsWith("/read"))
      return new Response(
        JSON.stringify({
          user_id: 2,
          last_read_at: "2026-10-29T10:00:00Z",
        }),
      );
    return new Response(JSON.stringify(message(9)));
  };
  const api = createMessagingApi("token", () => {});
  await api.send(7, "A reply", [], "reply-key", undefined, 12);
  await api.markRead(7, 9);
  const state = await api.readState(7);

  assert.deepEqual(requests[0], {
    url: "/api/v1/messaging/conversations/7/messages",
    body: {
      body: "A reply",
      attachment_ids: [],
      client_message_id: "reply-key",
      reply_to_message_id: 12,
    },
  });
  assert.equal(requests[1].url, "/api/v1/messaging/conversations/7/read");
  assert.deepEqual(requests[1].body, { last_message_id: 9 });
  assert.equal(requests[2].url, "/api/v1/messaging/conversations/7/read-state");
  assert.equal(state.members[0].user_id, 2);
  await api.message(7, 12);
  assert.equal(
    requests[3].url,
    "/api/v1/messaging/conversations/7/messages/12",
  );
});
test("binary session expiry signs out, provider internals stay hidden", async () => {
  let expired = 0;
  const api = createMessagingApi("token", () => expired++);
  globalThis.fetch = async () =>
    new Response('{"detail":"invalid"}', { status: 401 });
  await assert.rejects(api.download(1, 2));
  assert.equal(expired, 1);
  globalThis.fetch = async () =>
    new Response('{"detail":"private storage key"}', { status: 503 });
  await assert.rejects(
    api.download(1, 2),
    (e: Error) => !e.message.includes("storage key"),
  );
});
