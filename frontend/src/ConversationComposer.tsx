import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type RefObject,
} from "react";
import { errorMessage } from "./api";
import {
  checkFiles,
  type Attachment,
  type FilePolicy,
  type Message,
  type MessagingApi,
} from "./messaging-api";
type ComposerDraft = {
  body: string;
  files: File[];
  ready: Map<File, Attachment>;
  retry: { fingerprint: string; key: string } | null;
};
export type ReplyTarget = {
  id: number;
  senderName: string;
  body: string;
};
export type ComposerDrafts = RefObject<Map<number, ComposerDraft>>;
export function ConversationComposer({
  api,
  cid,
  policy,
  policyError,
  onSent,
  drafts,
  replyTo,
  onCancelReply,
}: {
  api: MessagingApi;
  cid: number;
  policy: FilePolicy | null;
  policyError: string;
  onSent: (m: Message) => void;
  drafts: ComposerDrafts;
  replyTo: ReplyTarget | null;
  onCancelReply: () => void;
}) {
  const [body, setBody] = useState(() => drafts.current.get(cid)?.body || "");
  const [files, setFiles] = useState<File[]>(
    () => drafts.current.get(cid)?.files || [],
  );
  const [ready, setReady] = useState<Map<File, Attachment>>(
    () => drafts.current.get(cid)?.ready || new Map(),
  );
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const operation = useRef<AbortController | null>(null);
  const retry = useRef<{ fingerprint: string; key: string } | null>(
    drafts.current.get(cid)?.retry || null,
  );
  const input = useRef<HTMLInputElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (replyTo) textarea.current?.focus();
  }, [replyTo]);
  useEffect(() => {
    drafts.current.set(cid, { body, files, ready, retry: retry.current });
  }, [body, files, ready, busy, cid, drafts]);
  useEffect(() => () => operation.current?.abort(), []);
  async function send(event: FormEvent) {
    event.preventDefault();
    if (operation.current || busy || !body.trim()) return;
    const controller = new AbortController();
    operation.current = controller;
    setError("");
    const uploaded = new Map(ready);
    try {
      if (files.length) {
        if (!policy)
          throw new Error("File settings could not be loaded. Try again.");
        if (files.length > policy.max_attachments)
          throw new Error(`Choose up to ${policy.max_attachments} files.`);
        const newFiles = files.filter((file) => !uploaded.has(file));
        if (newFiles.length) checkFiles(newFiles, policy);
      }
      for (const file of files) {
        if (uploaded.has(file)) continue;
        setBusy(`Uploading ${file.name}…`);
        const attachment = await api.upload(cid, file, controller.signal);
        uploaded.set(file, attachment);
        if (controller.signal.aborted) return;
        setReady(new Map(uploaded));
      }
      const ids = files.map((file) => uploaded.get(file)!.id);
      const fingerprint = JSON.stringify([
        body.trim(),
        ids,
        replyTo?.id ?? null,
      ]);
      if (retry.current?.fingerprint !== fingerprint)
        retry.current = { fingerprint, key: crypto.randomUUID() };
      setBusy("Sending…");
      const message = await api.send(
        cid,
        body,
        ids,
        retry.current.key,
        controller.signal,
        replyTo?.id,
      );
      if (!controller.signal.aborted) {
        onSent(message);
        setBody("");
        setFiles([]);
        setReady(new Map());
        retry.current = null;
        onCancelReply();
        if (input.current) input.current.value = "";
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      if (operation.current === controller) {
        operation.current = null;
        setBusy("");
      }
    }
  }
  function cancel() {
    operation.current?.abort();
    setError(
      "Transfer cancelled. Your draft is kept here. Unshared uploads expire automatically.",
    );
  }
  return (
    <form className="message-composer" onSubmit={send}>
      <label htmlFor={`message-${cid}`}>Message</label>
      {replyTo && (
        <div className="reply-composer">
          <div>
            <strong>Replying to {replyTo.senderName}</strong>
            <p>{replyTo.body}</p>
          </div>
          <button
            type="button"
            className="text-button"
            onClick={onCancelReply}
            disabled={!!busy}
            aria-label="Cancel reply"
          >
            Cancel
          </button>
        </div>
      )}
      <textarea
        ref={textarea}
        id={`message-${cid}`}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write a message to your team…"
        maxLength={10000}
        rows={3}
        required
        disabled={!!busy}
      />
      <p className="muted composer-hint">
        {files.length ? "Add a message to introduce your files. " : ""}
        {body.length.toLocaleString()} / 10,000
      </p>
      {files.length > 0 && (
        <ul className="draft-files">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              <span>
                {file.name}{" "}
                <small>
                  {ready.has(file)
                    ? "Ready to send"
                    : `${(file.size / 1024).toFixed(0)} KB`}
                </small>
              </span>
              <button
                type="button"
                className="text-button"
                disabled={!!busy}
                aria-label={`Remove ${file.name}`}
                onClick={async () => {
                  const attachment = ready.get(file);
                  setError("");
                  if (attachment) setBusy(`Removing ${file.name}…`);
                  try {
                    if (attachment) await api.remove(cid, attachment.id);
                    setFiles((current) => current.filter((f) => f !== file));
                    if (attachment) {
                      setReady((current) => {
                        const next = new Map(current);
                        next.delete(file);
                        return next;
                      });
                    }
                  } catch (cause) {
                    setError(errorMessage(cause));
                  } finally {
                    if (attachment) setBusy("");
                  }
                }}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
      <div className="composer-actions">
        <label
          className={`secondary file-picker ${!policy?.uploads_enabled || busy ? "file-picker-disabled" : ""}`}
        >
          Attach files
          <input
            ref={input}
            type="file"
            multiple
            accept={policy?.extensions.join(",")}
            disabled={!policy?.enabled || !policy.uploads_enabled || !!busy}
            onChange={(e) => {
              try {
                const selected = [
                  ...files,
                  ...Array.from(e.target.files || []),
                ];
                if (policy) checkFiles(selected, policy);
                setFiles(selected);
                setError("");
              } catch (cause) {
                setError(errorMessage(cause));
              }
              e.target.value = "";
            }}
          />
        </label>
        {busy && (
          <button type="button" className="secondary" onClick={cancel}>
            Cancel transfer
          </button>
        )}
        <span role="status" className="muted">
          {busy}
        </span>
        <button
          type="submit"
          className="primary"
          disabled={!!busy || !body.trim()}
        >
          Send message
        </button>
      </div>
      {!policy && (
        <p className="muted composer-hint">
          {policyError
            ? "File-sharing settings could not be loaded. Retry the request above."
            : "Checking file-sharing availability…"}
        </p>
      )}
      {policy && !policy.enabled && (
        <p className="muted composer-hint">
          File sharing is disabled for this workspace.
        </p>
      )}
      {policy?.enabled && !policy.uploads_enabled && (
        <p className="muted composer-hint">
          File uploads are unavailable until secure storage and safety scanning
          are configured.
        </p>
      )}
      {policy?.uploads_enabled && (
        <p className="muted composer-hint">
          TXT, PDF, PNG or JPEG · up to {Math.floor(policy.max_bytes / 1048576)}{" "}
          MB each · {policy.max_attachments} files per message
        </p>
      )}
    </form>
  );
}
