import { useEffect, useState, type FormEvent } from "react";
import { errorMessage } from "./api";
import {
  type Conversation,
  type MessagingApi,
  type Person,
} from "./messaging-api";
export function ConversationCreate({
  api,
  self,
  onCreated,
  onClose,
}: {
  api: MessagingApi;
  self: Person;
  onCreated: (c: Conversation) => void;
  onClose: () => void;
}) {
  const [group, setGroup] = useState(false),
    [name, setName] = useState(""),
    [search, setSearch] = useState("");
  const [people, setPeople] = useState<Person[]>([]),
    [selected, setSelected] = useState<Person[]>([]);
  const [after, setAfter] = useState(0),
    [more, setMore] = useState(false),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      api
        .people(search, after, controller.signal)
        .then((rows) => {
          if (!controller.signal.aborted) {
            setPeople((old) => (after ? [...old, ...rows] : rows));
            setMore(rows.length === 20);
          }
        })
        .catch((cause) => {
          if (!controller.signal.aborted) setError(errorMessage(cause));
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [api, search, after]);
  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy || !selected.length) return;
    setBusy(true);
    setError("");
    try {
      const created = group
        ? await api.group(
            name,
            selected.map((person) => person.id),
          )
        : await api.direct(selected[0].id);
      onCreated({ ...created, members: [self, ...selected] });
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="panel conversation-create"
      aria-labelledby="new-conversation-title"
    >
      <div className="section-heading">
        <h2 id="new-conversation-title">New conversation</h2>
        <button
          type="button"
          className="text-button"
          onClick={onClose}
          disabled={busy}
        >
          Cancel
        </button>
      </div>
      <form onSubmit={create}>
        <fieldset disabled={busy}>
          <label className="check-label">
            <input
              type="checkbox"
              checked={group}
              onChange={(e) => {
                setGroup(e.target.checked);
                setSelected([]);
              }}
            />{" "}
            Create a group
          </label>
          {group && (
            <label>
              Group name
              <input
                value={name}
                maxLength={255}
                required
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label>
            Find a colleague
            <input
              type="search"
              value={search}
              maxLength={100}
              onChange={(e) => {
                setSearch(e.target.value);
                setAfter(0);
                setPeople([]);
                setMore(false);
              }}
            />
          </label>
          {selected.length > 0 && (
            <p className="muted">
              Selected: {selected.map((p) => p.full_name).join(", ")}
            </p>
          )}
          <div
            className="people-options"
            aria-label="Colleagues"
            aria-busy={loading}
          >
            {people.map((person) => (
              <label key={person.id} className="check-label">
                <input
                  type={group ? "checkbox" : "radio"}
                  name="conversation-person"
                  checked={selected.some((p) => p.id === person.id)}
                  onChange={(e) => {
                    setSelected((old) =>
                      group
                        ? e.target.checked
                          ? [...old, person]
                          : old.filter((p) => p.id !== person.id)
                        : [person],
                    );
                  }}
                />
                {person.full_name}
              </label>
            ))}
            {loading && <p role="status">Finding colleagues…</p>}
            {!loading && !people.length && !error && (
              <p className="muted">No colleagues found.</p>
            )}
          </div>
          {more && (
            <button
              type="button"
              disabled={loading}
              className="secondary"
              onClick={() => setAfter(people.at(-1)?.id || 0)}
            >
              More colleagues
            </button>
          )}
          {error && (
            <p role="alert" className="notice error">
              {error}
            </p>
          )}
          <button
            className="primary"
            type="submit"
            disabled={
              !selected.length ||
              selected.length > 99 ||
              (group && !name.trim())
            }
          >
            {busy ? "Creating…" : group ? "Create group" : "Start conversation"}
          </button>
          {selected.length > 99 && (
            <p role="alert">Select up to 99 colleagues per group.</p>
          )}
        </fieldset>
      </form>
    </section>
  );
}
