import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, errorMessage, type Session } from "./api";
import { PageHeading, ErrorState, Empty } from "./ui";
import { Icon } from "./Icon";
import {
  ConversationComposer,
  type ComposerDrafts,
  type ReplyTarget,
} from "./ConversationComposer";
import { ConversationCreate } from "./ConversationCreate";
import {
  createMessagingApi,
  mergeMessages,
  titleFor,
  type Attachment,
  type Conversation,
  type FilePolicy,
  type Message,
  type MemberReadState,
  type MessagingApi,
} from "./messaging-api";
import "./messaging.css";

function SharedFile({
  api,
  cid,
  file,
  userId,
  changed,
}: {
  api: MessagingApi;
  cid: number;
  file: Attachment;
  userId: number;
  changed: (file: Attachment) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const transfer = useRef<AbortController | null>(null);
  const urls = useRef<string[]>([]);
  useEffect(
    () => () => {
      transfer.current?.abort();
      urls.current.forEach(URL.revokeObjectURL);
    },
    [],
  );
  const removed = file.status === "deleting" || file.status === "deleted";
  async function download() {
    if (transfer.current) return;
    const controller = new AbortController();
    transfer.current = controller;
    setBusy(true);
    setError("");
    try {
      const blob = await api.download(cid, file.id, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      urls.current.push(url);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        urls.current = urls.current.filter((u) => u !== url);
      }, 60000);
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      transfer.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className={`shared-file ${removed ? "removed-file" : ""}`}>
      <Icon name="file" />
      <div className="file-description">
        <strong>{file.filename}</strong>
        <small>
          {removed
            ? "Removed from this conversation"
            : `${(file.size_bytes / 1024).toFixed(0)} KB · ${file.content_type}`}
        </small>
      </div>
      {!removed && (
        <button
          className="secondary"
          onClick={download}
          disabled={busy}
          aria-label={`Download ${file.filename}`}
        >
          {busy ? "Downloading…" : "Download"}
        </button>
      )}
      {!removed && file.uploaded_by_user_id === userId && (
        <button
          className="text-button"
          disabled={busy}
          onClick={async () => {
            if (
              !window.confirm(`Remove ${file.filename} from this conversation?`)
            )
              return;
            setBusy(true);
            setError("");
            try {
              changed(await api.remove(cid, file.id));
            } catch (cause) {
              setError(errorMessage(cause));
            } finally {
              setBusy(false);
            }
          }}
        >
          Remove
        </button>
      )}
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
    </div>
  );
}
function ConversationFiles({
  api,
  cid,
  userId,
}: {
  api: MessagingApi;
  cid: number;
  userId: number;
}) {
  const [files, setFiles] = useState<Attachment[]>([]),
    [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  const load = useCallback(
    async (before: number | null) => {
      if (active.current) return;
      const controller = new AbortController();
      active.current = controller;
      setLoading(true);
      setError("");
      try {
        const page = await api.files(cid, before, controller.signal);
        if (!controller.signal.aborted) {
          setFiles((old) => (before ? [...old, ...page.items] : page.items));
          setCursor(page.next_cursor);
        }
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
        if (active.current === controller) active.current = null;
      }
    },
    [api, cid],
  );
  useEffect(() => {
    void load(null);
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [load]);
  return (
    <section className="conversation-files" aria-label="Shared files">
      <div className="section-heading">
        <h3>Shared in this conversation</h3>
        <button
          className="secondary"
          onClick={() => void load(null)}
          disabled={loading}
        >
          Refresh files
        </button>
      </div>
      {error && <ErrorState message={error} retry={() => void load(cursor)} />}
      {loading && <p role="status">Loading files…</p>}
      {!loading && !error && !files.length && (
        <Empty
          title="A place for shared work."
          text="Attach a file to a message to share it with this conversation."
        />
      )}
      {files.map((file) => (
        <SharedFile
          key={file.id}
          api={api}
          cid={cid}
          file={file}
          userId={userId}
          changed={(next) =>
            setFiles((old) => old.map((f) => (f.id === next.id ? next : f)))
          }
        />
      ))}
      {cursor && (
        <button
          className="secondary"
          disabled={loading}
          onClick={() => void load(cursor)}
        >
          Load more files
        </button>
      )}
    </section>
  );
}
function ConversationThread({
  api,
  conversation,
  session,
  policy,
  policyError,
  view,
  setView,
  back,
  drafts,
}: {
  api: MessagingApi;
  conversation: Conversation;
  session: Session;
  policy: FilePolicy | null;
  policyError: string;
  view: string;
  setView: (v: string) => void;
  back: () => void;
  drafts: ComposerDrafts;
}) {
  const [messages, setMessages] = useState<Message[]>([]),
    [cursor, setCursor] = useState<number | null>(null);
  const [readMembers, setReadMembers] = useState<MemberReadState[]>([]);
  const [replyTo, setReplyTo] = useState<ReplyTarget | null>(null);
  const [highlightedMessageId, setHighlightedMessageId] = useState<
    number | null
  >(null);
  const [loading, setLoading] = useState(true),
    [olderBusy, setOlderBusy] = useState(false),
    [error, setError] = useState(""),
    [denied, setDenied] = useState(false);
  const [revision, setRevision] = useState(0),
    [refreshing, setRefreshing] = useState(false);
  const older = useRef<AbortController | null>(null);
  const pendingJumpId = useRef<number | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const history = useRef<HTMLDivElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const newestId = useRef<number | null>(null);
  const firstPageLoaded = useRef(false);
  const memberNames = useMemo(
    () =>
      new Map(
        conversation.members.map((member) => [member.id, member.full_name]),
      ),
    [conversation.members],
  );
  const cid = conversation.id;
  useEffect(() => {
    if (view !== "messages") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        if (!document.hidden && navigator.onLine) {
          setRefreshing(true);
          const wasAtBottom =
            !firstPageLoaded.current ||
            !history.current ||
            history.current.scrollHeight -
              history.current.scrollTop -
              history.current.clientHeight <
              80;
          let next = newestId.current;
          let batches = 0;
          do {
            const page = next
              ? await api.updates(cid, next, controller.signal)
              : await api.messages(cid, null, controller.signal);
            if (controller.signal.aborted) return;
            setMessages((old) => mergeMessages(old, page.items));
            if (!firstPageLoaded.current || newestId.current === null) {
              setCursor(page.next_cursor);
              firstPageLoaded.current = true;
            }
            if (page.items.length) newestId.current = page.items.at(-1)!.id;
            next = next ? page.next_cursor : null;
            if (wasAtBottom && page.items.length)
              requestAnimationFrame(() =>
                bottom.current?.scrollIntoView({ block: "nearest" }),
              );
            batches++;
          } while (next && batches < 5);
          if (wasAtBottom && newestId.current !== null)
            await api.markRead(cid, newestId.current, controller.signal);
          const readState = await api.readState(cid, controller.signal);
          if (controller.signal.aborted) return;
          setReadMembers(readState.members);
          setError("");
          setDenied(false);
        }
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(errorMessage(cause));
          if (cause instanceof ApiError && [403, 404].includes(cause.status)) {
            setMessages([]);
            setReadMembers([]);
            newestId.current = null;
            firstPageLoaded.current = false;
            setDenied(true);
          }
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          setRefreshing(false);
          timer = setTimeout(refresh, 10000);
        }
      }
    }
    void refresh();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [api, cid, revision, view]);
  useEffect(
    () => () => {
      older.current?.abort();
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
    },
    [],
  );
  useEffect(() => {
    const messageId = pendingJumpId.current;
    if (messageId === null) return;
    const target = document.getElementById(`message-${cid}-${messageId}`);
    if (!target) return;
    pendingJumpId.current = null;
    setHighlightedMessageId(messageId);
    target.focus({ preventScroll: true });
    target.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "center",
    });
    if (highlightTimer.current) clearTimeout(highlightTimer.current);
    highlightTimer.current = setTimeout(
      () => setHighlightedMessageId(null),
      2400,
    );
  }, [cid, messages]);
  function focusMessage(messageId: number) {
    const target = document.getElementById(`message-${cid}-${messageId}`);
    if (target) {
      setHighlightedMessageId(messageId);
      target.focus({ preventScroll: true });
      target.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "center",
      });
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
      highlightTimer.current = setTimeout(
        () => setHighlightedMessageId(null),
        2400,
      );
      return;
    }

    pendingJumpId.current = messageId;
    void api
      .message(cid, messageId)
      .then((message) => setMessages((old) => mergeMessages(old, [message])))
      .catch((cause) => {
        pendingJumpId.current = null;
        setError(errorMessage(cause));
      });
  }
  function refreshHistory() {
    older.current?.abort();
    older.current = null;
    newestId.current = null;
    firstPageLoaded.current = false;
    setMessages([]);
    setReadMembers([]);
    setReplyTo(null);
    setCursor(null);
    setLoading(true);
    setRevision((revision) => revision + 1);
  }
  async function loadOlder() {
    if (!cursor || older.current) return;
    const controller = new AbortController();
    older.current = controller;
    const element = history.current,
      height = element?.scrollHeight || 0,
      top = element?.scrollTop || 0;
    setOlderBusy(true);
    try {
      const page = await api.messages(cid, cursor, controller.signal);
      if (!controller.signal.aborted) {
        setMessages((old) => mergeMessages(old, page.items));
        setCursor(page.next_cursor);
        setError("");
        requestAnimationFrame(() => {
          if (element) element.scrollTop = element.scrollHeight - height + top;
        });
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      if (!controller.signal.aborted) setOlderBusy(false);
      older.current = null;
    }
  }
  const otherMemberCount = conversation.members.filter(
    (member) => member.id !== session.id,
  ).length;
  return (
    <section
      className="conversation-thread"
      aria-label={titleFor(conversation, session.id)}
    >
      <header className="thread-heading">
        <button className="secondary thread-back" onClick={back}>
          ← Conversations
        </button>
        <div>
          <h2>{titleFor(conversation, session.id)}</h2>
          <p className="muted">
            {conversation.members.length} members ·{" "}
            {refreshing
              ? "Updating…"
              : "Checks for new messages every 10 seconds while visible"}
          </p>
        </div>
        <button
          className="secondary"
          onClick={refreshHistory}
          disabled={refreshing}
        >
          Refresh
        </button>
      </header>
      {policy?.enabled && (
        <div
          className="conversation-tabs"
          role="group"
          aria-label="Conversation view"
        >
          <button
            aria-pressed={view === "messages"}
            onClick={() => setView("messages")}
          >
            Messages
          </button>
          <button
            aria-pressed={view === "files"}
            onClick={() => setView("files")}
          >
            Files
          </button>
        </div>
      )}
      {view === "files" && policy?.enabled ? (
        <ConversationFiles key={cid} api={api} cid={cid} userId={session.id} />
      ) : (
        <>
          {error && <ErrorState message={error} retry={refreshHistory} />}
          <div
            className="message-history"
            ref={history}
            tabIndex={0}
            aria-label="Message history"
            aria-busy={loading}
          >
            {loading && <p role="status">Loading messages…</p>}
            {cursor && !denied && (
              <button
                className="secondary older-messages"
                disabled={olderBusy}
                onClick={loadOlder}
              >
                {olderBusy ? "Loading…" : "Load older messages"}
              </button>
            )}
            {!loading && !error && !messages.length && (
              <Empty
                title="Start the conversation."
                text="Share an update, ask a question, or send a file with a short message."
              />
            )}
            <ol className="message-list">
              {messages.map((message) => (
                <li
                  key={message.id}
                  className={
                    message.sender_id === session.id ? "message-own" : ""
                  }
                >
                  <article
                    id={`message-${cid}-${message.id}`}
                    tabIndex={-1}
                    className={
                      highlightedMessageId === message.id
                        ? "message-highlight"
                        : undefined
                    }
                  >
                    <header>
                      <strong>
                        {message.sender_id === session.id
                          ? "You"
                          : memberNames.get(message.sender_id) ||
                            `Member #${message.sender_id}`}
                      </strong>
                      <time dateTime={message.created_at}>
                        {new Date(message.created_at).toLocaleString(
                          undefined,
                          {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </time>
                    </header>
                    {message.reply_to && (
                      <button
                        type="button"
                        className="message-reply-preview"
                        onClick={() => focusMessage(message.reply_to!.id)}
                        aria-label={`Jump to message from ${memberNames.get(message.reply_to.sender_id) || "a conversation member"}`}
                      >
                        <strong>
                          {memberNames.get(message.reply_to.sender_id) ||
                            `Member #${message.reply_to.sender_id}`}
                        </strong>
                        <span>{message.reply_to.body}</span>
                      </button>
                    )}
                    <p className="message-body">{message.body}</p>
                    {message.attachments?.map((file) => (
                      <SharedFile
                        key={file.id}
                        api={api}
                        cid={cid}
                        file={file}
                        userId={session.id}
                        changed={(next) =>
                          setMessages((old) =>
                            old.map((m) => ({
                              ...m,
                              attachments: m.attachments.map((f) =>
                                f.id === next.id ? next : f,
                              ),
                            })),
                          )
                        }
                      />
                    ))}
                    <footer className="message-actions">
                      <button
                        type="button"
                        className="text-button"
                        onClick={() =>
                          setReplyTo({
                            id: message.id,
                            senderName:
                              message.sender_id === session.id
                                ? "You"
                                : memberNames.get(message.sender_id) ||
                                  `Member #${message.sender_id}`,
                            body: message.body,
                          })
                        }
                        aria-label={`Reply to message from ${message.sender_id === session.id ? "you" : memberNames.get(message.sender_id) || "a conversation member"}`}
                      >
                        Reply
                      </button>
                      {message.sender_id === session.id &&
                        otherMemberCount > 0 &&
                        (() => {
                          const seenBy = readMembers.filter((member) => {
                            if (
                              member.user_id === session.id ||
                              !member.last_read_at
                            )
                              return false;
                            return (
                              Date.parse(member.last_read_at) >=
                              Date.parse(message.created_at)
                            );
                          });
                          return (
                            <span
                              className="message-seen"
                              aria-label={
                                seenBy.length
                                  ? `Seen by ${seenBy
                                      .map(
                                        (member) =>
                                          memberNames.get(member.user_id) ||
                                          "a conversation member",
                                      )
                                      .join(", ")}`
                                  : "Not seen yet"
                              }
                            >
                              {seenBy.length
                                ? conversation.conversation_type === "direct"
                                  ? `Seen by ${memberNames.get(seenBy[0].user_id) || "member"}`
                                  : `Seen by ${seenBy.length} of ${otherMemberCount}`
                                : "Sent"}
                            </span>
                          );
                        })()}
                    </footer>
                  </article>
                </li>
              ))}
            </ol>
            <div ref={bottom} />
          </div>
          {!denied && (
            <ConversationComposer
              key={cid}
              api={api}
              cid={cid}
              policy={policy}
              policyError={policyError}
              drafts={drafts}
              replyTo={replyTo}
              onCancelReply={() => setReplyTo(null)}
              onSent={(message) => {
                setMessages((old) => mergeMessages(old, [message]));
                requestAnimationFrame(() =>
                  bottom.current?.scrollIntoView({ block: "nearest" }),
                );
              }}
            />
          )}
          <p className="sr-only" role="status">
            {messages.length} messages loaded.
          </p>
        </>
      )}
    </section>
  );
}
export function Messaging({
  session,
  signOut,
  initialView,
  policy,
}: {
  session: Session;
  signOut: (message?: string) => void;
  initialView: "messages" | "files";
  policy: {
    data: FilePolicy | null;
    error: string;
    reload: () => void;
  };
}) {
  const api = useMemo(
    () =>
      createMessagingApi(session.token, () =>
        signOut("Your session ended. Please sign in again."),
      ),
    [session.token, signOut],
  );
  const [conversations, setConversations] = useState<Conversation[]>([]),
    [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Conversation | null>(null),
    [creating, setCreating] = useState(false),
    [view, setView] = useState<string>(initialView);
  const [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  const drafts: ComposerDrafts = useRef(new Map());
  const load = useCallback(
    async (next: string | null) => {
      if (active.current) return;
      const controller = new AbortController();
      active.current = controller;
      setLoading(true);
      setError("");
      try {
        const page = await api.conversations(next, controller.signal);
        if (!controller.signal.aborted) {
          setConversations((old) =>
            next
              ? [
                  ...new Map(
                    [...old, ...page.items].map((c) => [c.id, c]),
                  ).values(),
                ]
              : page.items,
          );
          setCursor(page.next_cursor);
        }
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
        if (active.current === controller) active.current = null;
      }
    },
    [api],
  );
  useEffect(() => {
    void load(null);
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [load]);
  useEffect(() => setView(initialView), [initialView]);
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / CONNECT"
        title={
          initialView === "files"
            ? "Shared work, together."
            : "Keep the conversation going."
        }
        description={
          initialView === "files"
            ? "Choose a conversation to find its shared files."
            : "Talk directly, bring a group together, and share the work."
        }
      >
        <button
          className="primary"
          onClick={() => {
            setCreating(true);
            setSelected(null);
          }}
        >
          New conversation
        </button>
      </PageHeading>
      {policy.error && (
        <ErrorState message={policy.error} retry={policy.reload} />
      )}
      {creating && (
        <ConversationCreate
          api={api}
          self={{ id: session.id, full_name: session.name }}
          onClose={() => setCreating(false)}
          onCreated={(conversation) => {
            const summary = {
              ...conversation,
              members: conversation.members || [],
            };
            setCreating(false);
            setSelected(summary);
            setConversations((old) => [
              summary,
              ...old.filter((c) => c.id !== summary.id),
            ]);
            void load(null);
          }}
        />
      )}
      <div
        className={`messaging-workspace panel ${selected ? "has-conversation" : ""}`}
      >
        <aside className="conversation-sidebar" aria-label="Conversations">
          <div className="section-heading">
            <h2>Conversations</h2>
            <button
              className="text-button"
              onClick={() => void load(null)}
              disabled={loading}
            >
              Refresh
            </button>
          </div>
          {error && (
            <ErrorState message={error} retry={() => void load(cursor)} />
          )}
          {loading && (
            <p role="status" className="conversation-loading">
              Loading conversations…
            </p>
          )}
          {!loading && !error && !conversations.length && (
            <Empty
              title="Make a connection."
              text="Start a conversation with a colleague or create a group."
            />
          )}
          <ul className="conversation-list">
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  aria-current={selected?.id === c.id ? "true" : undefined}
                  onClick={() => {
                    setSelected(c);
                    setCreating(false);
                  }}
                >
                  <span className="avatar" aria-hidden="true">
                    <Icon
                      name={
                        c.conversation_type === "group" ? "people" : "message"
                      }
                    />
                  </span>
                  <span>
                    <strong>{titleFor(c, session.id)}</strong>
                    <small>
                      {c.conversation_type === "group"
                        ? "Group"
                        : "Direct message"}{" "}
                      · {c.members.length} members
                    </small>
                  </span>
                  <Icon name="chevron" />
                </button>
              </li>
            ))}
          </ul>
          {cursor && (
            <button
              className="secondary"
              disabled={loading}
              onClick={() => void load(cursor)}
            >
              Load more conversations
            </button>
          )}
        </aside>
        {selected ? (
          <ConversationThread
            key={selected.id}
            api={api}
            conversation={
              conversations.find((c) => c.id === selected.id) || selected
            }
            session={session}
            policy={policy.data}
            policyError={policy.error}
            drafts={drafts}
            view={view}
            setView={setView}
            back={() => setSelected(null)}
          />
        ) : (
          <div className="conversation-placeholder">
            <Icon name={initialView === "files" ? "file" : "message"} />
            <h2>
              {initialView === "files"
                ? "Every file has a shared place."
                : "Good work starts with a conversation."}
            </h2>
            <p className="muted">Choose a conversation, or start a new one.</p>
          </div>
        )}
      </div>
    </>
  );
}
