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
export type ComposerDrafts = RefObject<Map<number, ComposerDraft>>;
export function ConversationComposer({
  api,
  cid,
  policy,
  onSent,
  drafts,
}: {
  api: MessagingApi;
  cid: number;
  policy: FilePolicy | null;
  onSent: (m: Message) => void;
  drafts: ComposerDrafts;
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
        checkFiles(files, policy);
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
      const fingerprint = JSON.stringify([body.trim(), ids]);
      if (retry.current?.fingerprint !== fingerprint)
        retry.current = { fingerprint, key: crypto.randomUUID() };
      setBusy("Sending…");
      const message = await api.send(
        cid,
        body,
        ids,
        retry.current.key,
        controller.signal,
      );
      if (!controller.signal.aborted) {
        onSent(message);
        setBody("");
        setFiles([]);
        setReady(new Map());
        retry.current = null;
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
      <textarea
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
                onClick={() => {
                  const attachment = ready.get(file);
                  if (attachment)
                    void api.remove(cid, attachment.id).catch(() => {}); // TTL cleanup remains authoritative if offline.
                  setFiles(files.filter((f) => f !== file));
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
          className={`secondary file-picker ${!policy?.enabled || busy ? "file-picker-disabled" : ""}`}
        >
          Attach files
          <input
            ref={input}
            type="file"
            multiple
            accept={policy?.extensions.join(",")}
            disabled={!policy?.enabled || !!busy}
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
      {!policy?.enabled && (
        <p className="muted composer-hint">
          File sharing is unavailable until your workspace administrator
          configures secure storage.
        </p>
      )}
      {policy?.enabled && (
        <p className="muted composer-hint">
          TXT, PDF, PNG or JPEG · up to {Math.floor(policy.max_bytes / 1048576)}{" "}
          MB each · {policy.max_attachments} files per message
        </p>
      )}
    </form>
  );
}
