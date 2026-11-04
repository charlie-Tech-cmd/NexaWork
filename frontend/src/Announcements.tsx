import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { errorMessage, type Session } from "./api";
import { Empty, ErrorState, PageHeading } from "./ui";
import { createMessagingApi, type Announcement } from "./messaging-api";

export function Announcements({
  session,
  signOut,
}: {
  session: Session;
  signOut: (message?: string) => void;
}) {
  const api = useMemo(
    () =>
      createMessagingApi(session.token, () =>
        signOut("Your session ended. Please sign in again."),
      ),
    [session.token, signOut],
  );
  const [items, setItems] = useState<Announcement[]>([]);
  const [canPublish, setCanPublish] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal, before: number | null = null) => {
      if (before === null) setLoading(true);
      else setLoadingMore(true);
      setError("");
      try {
        const page = await api.announcements(before, signal);
        if (!signal?.aborted) {
          setItems((old) =>
            before
              ? [
                  ...new Map(
                    [...old, ...page.items].map((item) => [item.id, item]),
                  ).values(),
                ]
              : page.items,
          );
          setCanPublish(page.can_publish);
          setNextCursor(page.next_cursor);
        }
      } catch (cause) {
        if (!signal?.aborted) setError(errorMessage(cause));
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [api],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !title.trim() || !body.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await api.createAnnouncement(title, body);
      setItems((old) => [created, ...old]);
      setTitle("");
      setBody("");
      setCreating(false);
      setNotice("Announcement published to your organization.");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / UPDATES"
        title="Company announcements."
        description="Important updates from your organization, shared with every member."
      >
        {canPublish && (
          <button
            className="primary"
            onClick={() => {
              setCreating((value) => !value);
              setError("");
            }}
          >
            {creating ? "Cancel" : "Publish announcement"}
          </button>
        )}
      </PageHeading>
      {error && <ErrorState message={error} retry={() => void load()} />}
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {creating && canPublish && (
        <section className="panel announcement-create">
          <h2>New organization announcement</h2>
          <p className="muted">
            This will be visible to all active members of your organization.
          </p>
          <form className="data-form" onSubmit={publish}>
            <fieldset disabled={busy}>
              <label>
                Headline
                <input
                  autoFocus
                  required
                  maxLength={255}
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <label>
                Announcement
                <textarea
                  required
                  maxLength={10000}
                  rows={6}
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                />
              </label>
              <button className="primary" type="submit">
                {busy ? "Publishing…" : "Publish"}
              </button>
            </fieldset>
          </form>
        </section>
      )}
      {loading ? (
        <p role="status">Loading announcements…</p>
      ) : !error && !items.length ? (
        <Empty
          title="A clear space for important updates."
          text="Organization announcements will appear here when they are published."
        />
      ) : (
        <>
          <section className="announcement-list" aria-label="Announcements">
            {items.map((item) => (
              <article className="panel announcement-card" key={item.id}>
                <header>
                  <div>
                    <p className="eyebrow">ORGANIZATION UPDATE</p>
                    <h2>{item.title}</h2>
                  </div>
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </time>
                </header>
                <p className="announcement-body">{item.body}</p>
                <footer>
                  Published by <strong>{item.author_name}</strong>
                </footer>
              </article>
            ))}
          </section>
          {nextCursor && (
            <button
              className="secondary"
              disabled={loadingMore}
              onClick={() => void load(undefined, nextCursor)}
            >
              {loadingMore ? "Loading…" : "Load older announcements"}
            </button>
          )}
        </>
      )}
    </>
  );
}
