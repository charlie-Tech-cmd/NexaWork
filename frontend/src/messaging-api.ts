import { ApiError, request } from "./api.ts";
export type Person = { id: number; full_name: string };
export type Conversation = {
  id: number;
  name: string | null;
  conversation_type: "direct" | "group" | "channel";
  channel_visibility?: "public" | "private" | null;
  members: Person[];
};
export type Channel = {
  id: number;
  name: string;
  visibility: "public" | "private";
  is_member: boolean;
  membership_role: "member" | "moderator" | null;
  member_count: number;
  members: Person[];
  created_by_user_id: number;
  created_at: string;
};
export type ChannelMember = {
  user_id: number;
  full_name: string;
  role: "member" | "moderator";
  joined_at: string;
};
export type Announcement = {
  id: number;
  title: string;
  body: string;
  created_by_user_id: number;
  author_name: string;
  created_at: string;
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
export type MessageReply = {
  id: number;
  sender_id: number;
  body: string;
};
export type Message = {
  id: number;
  sender_id: number;
  body: string;
  created_at: string;
  attachments: Attachment[];
  reply_to?: MessageReply | null;
};
export type MemberReadState = {
  user_id: number;
  last_read_at: string | null;
};
export type Page<T, C = number> = { items: T[]; next_cursor: C | null };
export type FilePolicy = {
  enabled: boolean;
  uploads_enabled: boolean;
  max_bytes: number;
  max_attachments: number;
  extensions: string[];
};

function isFilePolicy(value: unknown): value is FilePolicy {
  if (!value || typeof value !== "object") return false;
  const policy = value as Record<string, unknown>;
  return (
    typeof policy.enabled === "boolean" &&
    typeof policy.uploads_enabled === "boolean" &&
    (!policy.uploads_enabled || policy.enabled) &&
    typeof policy.max_bytes === "number" &&
    Number.isInteger(policy.max_bytes) &&
    policy.max_bytes > 0 &&
    typeof policy.max_attachments === "number" &&
    Number.isInteger(policy.max_attachments) &&
    policy.max_attachments > 0 &&
    Array.isArray(policy.extensions) &&
    policy.extensions.every((extension) => typeof extension === "string")
  );
}
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
  if (!policy.uploads_enabled)
    throw new Error("File uploads are not configured for this workspace.");
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
  async function requestJson<T>(
    path: string,
    method = "GET",
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    try {
      return (await request(path, token, method, body, signal)) as T;
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) expired();
      throw cause;
    }
  }
  function json<T>(
    path: string,
    method = "GET",
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    return requestJson(`/messaging${path}`, method, body, signal);
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
    channels: async (signal?: AbortSignal) =>
      requestJson<{ items: Channel[]; can_create: boolean }>(
        "/channels",
        "GET",
        undefined,
        signal,
      ),
    createChannel: (name: string, visibility: Channel["visibility"]) =>
      requestJson<
        Channel & { organization_id: number; conversation_type: "channel" }
      >("/channels", "POST", { name, visibility }),
    joinChannel: (id: number) =>
      requestJson<
        Channel & { organization_id: number; conversation_type: "channel" }
      >(`/channels/${id}/join`, "POST"),
    channelMembers: (id: number, signal?: AbortSignal) =>
      requestJson<ChannelMember[]>(
        `/channels/${id}/members`,
        "GET",
        undefined,
        signal,
      ),
    addChannelMember: (id: number, userId: number) =>
      requestJson<ChannelMember>(`/channels/${id}/members`, "POST", {
        user_id: userId,
      }),
    setChannelMemberRole: (
      id: number,
      userId: number,
      role: ChannelMember["role"],
    ) =>
      requestJson<ChannelMember>(`/channels/${id}/members/${userId}`, "PATCH", {
        role,
      }),
    removeChannelMember: (id: number, userId: number) =>
      requestJson<null>(`/channels/${id}/members/${userId}`, "DELETE"),
    announcements: async (before: number | null, signal?: AbortSignal) =>
      requestJson<{
        items: Announcement[];
        can_publish: boolean;
        next_cursor: number | null;
      }>(
        `/announcements?limit=50${before ? `&before_id=${before}` : ""}`,
        "GET",
        undefined,
        signal,
      ),
    createAnnouncement: (title: string, body: string) =>
      requestJson<Announcement>("/announcements", "POST", { title, body }),
    messages: (cid: number, before: number | null, signal?: AbortSignal) =>
      json<Page<Message>>(
        `/conversations/${cid}/messages?limit=50${before ? `&before_id=${before}` : ""}`,
        "GET",
        undefined,
        signal,
      ),
    message: (cid: number, messageId: number, signal?: AbortSignal) =>
      json<Message>(
        `/conversations/${cid}/messages/${messageId}`,
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
    markRead: (cid: number, lastMessageId: number, signal?: AbortSignal) =>
      json<MemberReadState>(
        `/conversations/${cid}/read`,
        "POST",
        { last_message_id: lastMessageId },
        signal,
      ),
    readState: (cid: number, signal?: AbortSignal) =>
      json<{ members: MemberReadState[] }>(
        `/conversations/${cid}/read-state`,
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
      reply_to_message_id?: number | null,
    ) =>
      json<Message>(
        `/conversations/${cid}/messages`,
        "POST",
        {
          body,
          attachment_ids,
          client_message_id,
          ...(reply_to_message_id ? { reply_to_message_id } : {}),
        },
        signal,
      ),
    policy: async (signal?: AbortSignal) => {
      const value = await json<unknown>(
        "/file-policy",
        "GET",
        undefined,
        signal,
      );
      if (!isFilePolicy(value))
        throw new ApiError(
          "File-sharing settings returned an unexpected response.",
        );
      return value;
    },
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
