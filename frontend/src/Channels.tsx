import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { errorMessage, type Session } from "./api";
import { Empty, ErrorState, PageHeading } from "./ui";
import {
  createMessagingApi,
  type Channel,
  type ChannelMember,
  type Conversation,
  type FilePolicy,
  type MessagingApi,
  type Person,
} from "./messaging-api";
import { ConversationThread } from "./Messaging";
import type { ComposerDrafts } from "./ConversationComposer";
import "./messaging.css";

function ChannelPeople({
  api,
  channel,
  session,
  changed,
}: {
  api: MessagingApi;
  channel: Channel;
  session: Session;
  changed: () => void;
}) {
  const [members, setMembers] = useState<ChannelMember[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [search, setSearch] = useState("");
  const [selectedPerson, setSelectedPerson] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const active = useRef<AbortController | null>(null);

  const loadMembers = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError("");
    try {
      const rows = await api.channelMembers(channel.id, controller.signal);
      if (!controller.signal.aborted) setMembers(rows);
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      if (active.current === controller) active.current = null;
    }
  }, [api, channel.id]);

  useEffect(() => {
    void loadMembers();
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [loadMembers]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api
        .people(search, 0, controller.signal)
        .then((rows) => {
          if (!controller.signal.aborted) setPeople(rows);
        })
        .catch((cause) => {
          if (!controller.signal.aborted) setError(errorMessage(cause));
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [api, search]);

  const isModerator = channel.membership_role === "moderator";
  const activeModerators = members.filter(
    (member) => member.role === "moderator",
  ).length;
  const candidates = people.filter(
    (person) => !members.some((member) => member.user_id === person.id),
  );

  async function changeMember(
    action: () => Promise<unknown>,
    success: string,
  ): Promise<boolean> {
    if (busy) return false;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(success);
      await loadMembers();
      changed();
      return true;
    } catch (cause) {
      setError(errorMessage(cause));
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="channel-members panel" aria-labelledby="channel-people">
      <header className="section-heading">
        <h3 id="channel-people">Members and moderators</h3>
        <button
          className="text-button"
          onClick={() => void loadMembers()}
          disabled={loading || busy}
        >
          Refresh
        </button>
      </header>
      {error && <ErrorState message={error} retry={() => void loadMembers()} />}
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {loading ? (
        <p role="status">Loading channel members…</p>
      ) : (
        <ul className="channel-member-list">
          {members.map((member) => (
            <li key={member.user_id}>
              <span>
                <strong>
                  {member.user_id === session.id ? "You" : member.full_name}
                </strong>
                <small>
                  {" "}
                  {member.role === "moderator" ? "Moderator" : "Member"}
                </small>
              </span>
              {isModerator && (
                <div className="channel-member-actions">
                  <label>
                    <span className="sr-only">Role for {member.full_name}</span>
                    <select
                      value={member.role}
                      disabled={busy}
                      onChange={(event) =>
                        void changeMember(
                          () =>
                            api.setChannelMemberRole(
                              channel.id,
                              member.user_id,
                              event.target.value === "moderator"
                                ? "moderator"
                                : "member",
                            ),
                          "Channel role updated.",
                        )
                      }
                    >
                      <option value="member">Member</option>
                      <option value="moderator">Moderator</option>
                    </select>
                  </label>
                  <button
                    className="text-button"
                    disabled={
                      busy ||
                      (member.role === "moderator" && activeModerators < 2)
                    }
                    onClick={() => {
                      const action =
                        member.user_id === session.id
                          ? "Leave this channel?"
                          : `Remove ${member.full_name} from this channel?`;
                      if (window.confirm(action)) {
                        void changeMember(
                          () =>
                            api.removeChannelMember(channel.id, member.user_id),
                          member.user_id === session.id
                            ? "You left the channel."
                            : "Member removed.",
                        );
                      }
                    }}
                  >
                    {member.user_id === session.id ? "Leave" : "Remove"}
                  </button>
                </div>
              )}
              {!isModerator && member.user_id === session.id && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm("Leave this channel?")) {
                      void changeMember(
                        () => api.removeChannelMember(channel.id, session.id),
                        "You left the channel.",
                      );
                    }
                  }}
                >
                  Leave
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {isModerator && (
        <form
          className="channel-add-member"
          onSubmit={(event) => {
            event.preventDefault();
            const userId = Number(selectedPerson);
            if (!userId || busy) return;
            void changeMember(
              () => api.addChannelMember(channel.id, userId),
              "Member added to the channel.",
            ).then((succeeded) => {
              if (succeeded) setSelectedPerson("");
            });
          }}
        >
          <label>
            Find a colleague to add
            <input
              type="search"
              maxLength={100}
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setSelectedPerson("");
              }}
            />
          </label>
          <label>
            Colleague
            <select
              value={selectedPerson}
              onChange={(event) => setSelectedPerson(event.target.value)}
              disabled={busy}
            >
              <option value="">Choose a colleague</option>
              {candidates.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.full_name}
                </option>
              ))}
            </select>
          </label>
          {!candidates.length && search && (
            <p className="muted">No available colleagues found.</p>
          )}
          <button
            className="secondary"
            type="submit"
            disabled={busy || !selectedPerson}
          >
            {busy ? "Updating…" : "Add member"}
          </button>
        </form>
      )}
      {isModerator && activeModerators === 1 && (
        <p className="muted">
          Add another moderator before leaving or removing the last moderator.
        </p>
      )}
    </section>
  );
}

export function Channels({
  session,
  signOut,
  policy,
}: {
  session: Session;
  signOut: (message?: string) => void;
  policy: { data: FilePolicy | null; error: string; reload: () => void };
}) {
  const api = useMemo(
    () =>
      createMessagingApi(session.token, () =>
        signOut("Your session ended. Please sign in again."),
      ),
    [session.token, signOut],
  );
  const [channels, setChannels] = useState<Channel[]>([]);
  const [canCreate, setCanCreate] = useState(false);
  const [selected, setSelected] = useState<Channel | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [visibility, setVisibility] = useState<Channel["visibility"]>("public");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [view, setView] = useState("messages");
  const active = useRef<AbortController | null>(null);
  const drafts: ComposerDrafts = useRef(new Map());

  const load = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError("");
    try {
      const response = await api.channels(controller.signal);
      if (!controller.signal.aborted) {
        setChannels(response.items);
        setCanCreate(response.can_create);
        setSelected((current) =>
          current
            ? response.items.find((channel) => channel.id === current.id) ||
              null
            : null,
        );
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      if (active.current === controller) active.current = null;
    }
  }, [api]);

  useEffect(() => {
    void load();
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [load]);

  async function createChannel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !name.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await api.createChannel(name, visibility);
      const channel: Channel = {
        ...created,
        members: created.members || [],
      };
      setChannels((old) =>
        [...old.filter((item) => item.id !== channel.id), channel].sort(
          (a, b) => a.name.localeCompare(b.name),
        ),
      );
      setSelected(channel);
      setCreating(false);
      setName("");
      setVisibility("public");
      setView("messages");
      setNotice("Channel created.");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  async function join(channel: Channel) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const joined = await api.joinChannel(channel.id);
      const next: Channel = { ...joined, members: joined.members || [] };
      setChannels((old) =>
        old.map((item) => (item.id === channel.id ? next : item)),
      );
      setSelected(next);
      setView("messages");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  const conversation: Conversation | null = selected?.is_member
    ? {
        id: selected.id,
        name: selected.name,
        conversation_type: "channel",
        channel_visibility: selected.visibility,
        members: selected.members,
      }
    : null;

  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / COLLABORATE"
        title="Channels for shared work."
        description="Find your team spaces, join public channels, or create a private place to collaborate."
      >
        {canCreate && (
          <button
            className="primary"
            onClick={() => {
              setCreating((value) => !value);
              setSelected(null);
              setError("");
            }}
          >
            {creating ? "Cancel" : "Create channel"}
          </button>
        )}
      </PageHeading>
      {policy.error && (
        <ErrorState message={policy.error} retry={policy.reload} />
      )}
      {error && <ErrorState message={error} retry={() => void load()} />}
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {creating && (
        <section className="panel channel-create">
          <h2>Create a channel</h2>
          <form className="data-form" onSubmit={createChannel}>
            <fieldset disabled={busy}>
              <label>
                Channel name
                <input
                  autoFocus
                  required
                  maxLength={255}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <label>
                Who can join?
                <select
                  value={visibility}
                  onChange={(event) =>
                    setVisibility(event.target.value as Channel["visibility"])
                  }
                >
                  <option value="public">
                    Public — anyone in your organization can join
                  </option>
                  <option value="private">
                    Private — moderators invite members
                  </option>
                </select>
              </label>
              <button className="primary" type="submit">
                {busy ? "Creating…" : "Create channel"}
              </button>
            </fieldset>
          </form>
        </section>
      )}
      <div
        className={`messaging-workspace panel ${selected ? "has-conversation" : ""}`}
      >
        <aside className="conversation-sidebar" aria-label="Channels">
          <div className="section-heading">
            <h2>Channels</h2>
            <button
              className="text-button"
              onClick={() => void load()}
              disabled={loading}
            >
              Refresh
            </button>
          </div>
          {loading && (
            <p role="status" className="conversation-loading">
              Loading channels…
            </p>
          )}
          {!loading && !error && !channels.length && (
            <Empty
              title="Your shared space starts here."
              text="Create a channel or ask an administrator to set one up."
            />
          )}
          <ul className="channel-list">
            {channels.map((channel) => (
              <li key={channel.id}>
                <button
                  className="channel-select"
                  aria-current={
                    selected?.id === channel.id ? "true" : undefined
                  }
                  onClick={() => {
                    setSelected(channel);
                    setCreating(false);
                    setView("messages");
                    setNotice("");
                  }}
                >
                  <span className="channel-symbol" aria-hidden="true">
                    {channel.visibility === "private" ? "▣" : "#"}
                  </span>
                  <span>
                    <strong>{channel.name}</strong>
                    <small>
                      {channel.visibility === "private" ? "Private" : "Public"}{" "}
                      · {channel.member_count} members
                    </small>
                  </span>
                </button>
                {channel.visibility === "public" && !channel.is_member && (
                  <button
                    className="secondary channel-join"
                    disabled={busy}
                    onClick={() => void join(channel)}
                  >
                    Join
                  </button>
                )}
              </li>
            ))}
          </ul>
        </aside>
        {selected && conversation ? (
          <div className="channel-detail">
            <ConversationThread
              key={selected.id}
              api={api}
              conversation={conversation}
              session={session}
              policy={policy.data}
              policyError={policy.error}
              drafts={drafts}
              view={view}
              setView={setView}
              back={() => setSelected(null)}
            />
            <ChannelPeople
              api={api}
              channel={selected}
              session={session}
              changed={() => void load()}
            />
          </div>
        ) : selected ? (
          <section className="conversation-placeholder channel-preview">
            <span className="channel-symbol" aria-hidden="true">
              #
            </span>
            <h2>{selected.name}</h2>
            <p className="muted">
              Public channel · {selected.member_count} members
            </p>
            <p>Join to read and contribute to this channel.</p>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void join(selected)}
            >
              {busy ? "Joining…" : "Join channel"}
            </button>
          </section>
        ) : (
          <div className="conversation-placeholder">
            <span className="channel-symbol" aria-hidden="true">
              #
            </span>
            <h2>Make room for shared work.</h2>
            <p className="muted">
              Choose a channel, or join a public space to get started.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
