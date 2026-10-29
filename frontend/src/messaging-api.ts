import { ApiError, request } from "./api.ts";
export type Person = { id: number; full_name: string };
export type Conversation = {
  id: number;
  name: string | null;
  conversation_type: "direct" | "group";
  members: Person[];
};
export type Attachment = {
  id: number;
  conversation_id: number;
  message_id: number | null;
  uploaded_by_user_id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "uploading" | "ready" | "attached" | "deleting" | "deleted";
  created_at: string;
};
export type Message = {
  id: number;
  sender_id: number;
  body: string;
  created_at: string;
  attachments: Attachment[];
};
export type Page<T, C = number> = { items: T[]; next_cursor: C | null };
export type FilePolicy = {
  enabled: boolean;
  max_bytes: number;
  max_attachments: number;
  extensions: string[];
};
export function mergeMessages(
  current: Message[],
  incoming: Message[],
): Message[] {
  return [
    ...new Map([...current, ...incoming].map((m) => [m.id, m])).values(),
  ].sort((a, b) => a.id - b.id);
}
export function titleFor(c: Conversation, userId: number): string {
  return (
    c.name ||
    c.members
      .filter((m) => m.id !== userId)
      .map((m) => m.full_name)
      .join(", ") ||
    "Direct conversation"
  );
}
export function checkFiles(files: File[], policy: FilePolicy): void {
  if (!policy.enabled)
    throw new Error("File sharing is not configured for this workspace.");
  if (files.length > policy.max_attachments)
    throw new Error(`Choose up to ${policy.max_attachments} files.`);
  for (const file of files) {
    if (!file.size || file.size > policy.max_bytes)
      throw new Error(
        `${file.name}: choose a nonempty file under ${Math.floor(policy.max_bytes / 1048576)} MB.`,
      );
    if (
      !policy.extensions.includes(
        `.${file.name.split(".").pop()?.toLowerCase()}`,
      )
    )
      throw new Error(`${file.name}: this file type is not supported.`);
  }
}
export function createMessagingApi(token: string, expired: () => void) {
  async function json<T>(
    path: string,
    method = "GET",
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    try {
      return (await request(
        `/messaging${path}`,
        token,
        method,
        body,
        signal,
      )) as T;
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) expired();
      throw cause;
    }
  }
  async function binary(
    path: string,
    init: RequestInit,
    signal?: AbortSignal,
  ): Promise<Response> {
    let response: Response;
    try {
      response = await fetch(`/api/v1/messaging${path}`, {
        ...init,
        headers: { ...init.headers, Authorization: `Bearer ${token}` },
        credentials: "omit",
        redirect: "error",
        cache: "no-store",
        signal: signal
          ? AbortSignal.any([signal, AbortSignal.timeout(150000)])
          : AbortSignal.timeout(150000),
      });
    } catch (cause) {
      if (signal?.aborted) throw cause;
      throw new ApiError(
        "The transfer could not finish. Check your connection and try again.",
      );
    }
    if (response.status === 401) expired();
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new ApiError(
        response.status < 500 && typeof body?.detail === "string"
          ? body.detail
          : "The transfer is temporarily unavailable. Please try again.",
        response.status,
      );
    }
    return response;
  }
  return {
    conversations: (cursor: string | null, signal?: AbortSignal) =>
      json<Page<Conversation, string>>(
        `/conversations/page?limit=30${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
        "GET",
        undefined,
        signal,
      ),
    people: (search: string, after: number, signal?: AbortSignal) =>
      json<Person[]>(
        `/people?limit=20&search=${encodeURIComponent(search)}&after_id=${after}`,
        "GET",
        undefined,
        signal,
      ),
    direct: (id: number) =>
      json<Conversation>("/direct", "POST", { recipient_user_id: id }),
    group: (name: string, ids: number[]) =>
      json<Conversation>("/groups", "POST", { name, member_user_ids: ids }),
    messages: (cid: number, before: number | null, signal?: AbortSignal) =>
      json<Page<Message>>(
        `/conversations/${cid}/messages?limit=50${before ? `&before_id=${before}` : ""}`,
        "GET",
        undefined,
        signal,
      ),
    updates: (cid: number, after: number, signal?: AbortSignal) =>
      json<Page<Message>>(
        `/conversations/${cid}/updates?limit=50&after_id=${after}`,
        "GET",
        undefined,
        signal,
      ),
    send: (
      cid: number,
      body: string,
      attachment_ids: number[],
      client_message_id: string,
      signal?: AbortSignal,
    ) =>
      json<Message>(
        `/conversations/${cid}/messages`,
        "POST",
        { body, attachment_ids, client_message_id },
        signal,
      ),
    policy: (signal?: AbortSignal) =>
      json<FilePolicy>("/file-policy", "GET", undefined, signal),
    files: (cid: number, before: number | null, signal?: AbortSignal) =>
      json<Page<Attachment>>(
        `/conversations/${cid}/attachments?limit=30${before ? `&before_id=${before}` : ""}`,
        "GET",
        undefined,
        signal,
      ),
    upload: async (cid: number, file: File, signal: AbortSignal) =>
      (
        await binary(
          `/conversations/${cid}/attachments`,
          {
            method: "POST",
            body: file,
            headers: {
              "Content-Type": "application/octet-stream",
              "X-Filename": encodeURIComponent(file.name),
            },
          },
          signal,
        )
      ).json() as Promise<Attachment>,
    download: async (cid: number, aid: number, signal?: AbortSignal) =>
      (
        await binary(
          `/conversations/${cid}/attachments/${aid}/download`,
          { method: "GET" },
          signal,
        )
      ).blob(),
    remove: (cid: number, aid: number) =>
      json<Attachment>(`/conversations/${cid}/attachments/${aid}`, "DELETE"),
  };
}
export type MessagingApi = ReturnType<typeof createMessagingApi>;
