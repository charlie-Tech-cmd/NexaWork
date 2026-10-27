import Landing from "./landing/Landing";
import { publicView } from "./landing/content";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  record,
  request,
  type RecordData,
  type Session,
} from "./api";
import { Auth } from "./Auth";
import { Directory, type Call } from "./Directory";
import { Structure } from "./Structure";
import { Roles } from "./Roles";
import { DataForm, ErrorState, PageHeading, Status } from "./ui";
import { useResource } from "./useResource";
const navigation = [
  { id: "overview", label: "Overview", icon: "◫" },
  { id: "people", label: "People", icon: "♧" },
  { id: "structure", label: "Organization", icon: "▦" },
  { id: "roles", label: "Roles & access", icon: "◇" },
  { id: "settings", label: "Settings", icon: "⚙" },
];
function Overview({
  session,
  organization,
  navigate,
}: {
  session: Session;
  organization: RecordData;
  navigate: (page: string) => void;
}) {
  return (
    <>
      <PageHeading
        eyebrow="YOUR WORKSPACE"
        title={`Hello, ${session.name.split(" ")[0] || "there"}.`}
        description="A little clarity for the work ahead."
      />
      <section className="welcome-banner">
        <div>
          <span className="banner-tag">ALL TOGETHER, IN ONE PLACE</span>
          <h2>
            Your people.
            <br />
            Your shared space.
          </h2>
          <p>
            Keep your organization connected, from the
            <br className="desktop-break" /> first region to every team within
            it.
          </p>
          <button onClick={() => navigate("structure")}>
            Explore your organization <span>↗</span>
          </button>
        </div>
        <div className="workspace-art" aria-hidden="true">
          <span className="art-label">{String(organization.name)}</span>
          <div className="art-line" />
          <div className="art-nodes">
            <span>◎</span>
            <span>⌂</span>
            <span>◇</span>
          </div>
          <div className="art-caption">A connected workspace</div>
        </div>
      </section>
      <div className="section-heading">
        <h2>Your everyday essentials</h2>
        <span className="muted">A good place to start</span>
      </div>
      <div className="quick-grid">
        {[
          {
            page: "people",
            icon: "♧",
            name: "Bring people together",
            text: "Find a colleague or add someone new.",
            action: "Open directory",
          },
          {
            page: "structure",
            icon: "▦",
            name: "See the bigger picture",
            text: "Explore regions, branches, departments and teams.",
            action: "Explore organization",
          },
          {
            page: "roles",
            icon: "◇",
            name: "Make access clear",
            text: "See workspace roles and their permissions.",
            action: "View roles",
          },
        ].map((item) => (
          <button
            className="quick-card"
            key={item.page}
            onClick={() => navigate(item.page)}
          >
            <span className="structure-icon" aria-hidden="true">
              {item.icon}
            </span>
            <h3>{item.name}</h3>
            <p className="muted">{item.text}</p>
            <span className="card-link">
              {item.action} <span>→</span>
            </span>
          </button>
        ))}
      </div>
      <section className="workspace-strip">
        <div>
          <span className="eyebrow">CURRENT ORGANIZATION</span>
          <h3>{String(organization.name)}</h3>
          <p className="muted">{String(organization.slug)}</p>
        </div>
        <Status active={organization.is_active} />
        <div>
          <span className="muted">Signed in as</span>
          <p>
            <strong>{session.name}</strong>
          </p>
          <span className="muted">
            {session.mode === "admin"
              ? "Administrator sign-in"
              : "Member sign-in"}
          </span>
        </div>
      </section>
    </>
  );
}
function Settings({
  organization,
  call,
  reload,
  session,
}: {
  organization: RecordData;
  call: Call;
  reload: () => void;
  session: Session;
}) {
  const [notice, setNotice] = useState("");
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / SETTINGS"
        title="Workspace details."
        description="Keep your organization's identity up to date."
      />
      <section className="settings-grid">
        <div className="panel settings-panel">
          <h2>Organization</h2>
          <p className="muted">
            Changes require organization update permission.
          </p>
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          <DataForm
            fields={[
              {
                name: "name",
                label: "Organization name",
                value: String(organization.name),
                minLength: 2,
              },
              {
                name: "slug",
                label: "Organization handle",
                value: String(organization.slug),
                minLength: 2,
                maxLength: 100,
              },
            ]}
            submit="Save changes"
            onSave={async (data) => {
              await call("/organizations/me", "PATCH", data);
              setNotice("Organization updated.");
              reload();
            }}
          />
        </div>
        <div className="panel settings-panel">
          <h2>Your account</h2>
          <dl>
            <dt>Full name</dt>
            <dd>{session.name}</dd>
            <dt>Email address</dt>
            <dd>{session.email}</dd>
            <dt>Session</dt>
            <dd>{session.mode === "admin" ? "Administrator" : "Member"}</dd>
          </dl>
          <p className="muted">
            Your session is kept only in this tab's memory. Refreshing or
            closing the page signs you out.
          </p>
        </div>
      </section>
    </>
  );
}
function Workspace({
  session,
  signOut,
}: {
  session: Session;
  signOut: (message?: string) => void;
}) {
  const [page, setPage] = useState("overview");
  const [menu, setMenu] = useState(false);
  const main = useRef<HTMLElement>(null);
  const call: Call = useCallback(
    async (path, method = "GET", body, signal) => {
      try {
        return await request(path, session.token, method, body, signal);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401)
          signOut("Your session ended. Please sign in again.");
        throw error;
      }
    },
    [session.token, signOut],
  );
  const organization = useResource(
    async (signal) =>
      record(await call("/organizations/me", "GET", undefined, signal)),
    [session.id],
  );
  function navigate(next: string) {
    setPage(next);
    setMenu(false);
  }
  useEffect(() => {
    document.title = `${navigation.find((item) => item.id === page)?.label} · NexaWork`;
    main.current?.focus();
  }, [page]);
  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <a
          className="brand"
          href="#overview"
          onClick={(event) => {
            event.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-mark">N</span>NexaWork
          <span className="brand-dot">•</span>
        </a>
        <div className="workspace-picker">
          <span className="workspace-initial" aria-hidden="true">
            {String(organization.data?.name || "W").slice(0, 1)}
          </span>
          <div>
            <strong>
              {String(organization.data?.name || "Your workspace")}
            </strong>
            <small>Organization workspace</small>
          </div>
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Workspace navigation">
          {navigation.map((item) => (
            <button
              key={item.id}
              aria-current={page === item.id ? "page" : undefined}
              onClick={() => navigate(item.id)}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
              {page === item.id && (
                <span className="nav-indicator" aria-hidden="true">
                  •
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span aria-hidden="true">◎</span>
            <strong>Built around your people.</strong>
            <p>A shared space to keep everyone connected.</p>
          </div>
          <div className="sidebar-profile">
            <span className="avatar">{session.name.slice(0, 1)}</span>
            <div>
              <strong>{session.name}</strong>
              <small>
                {session.mode === "admin" ? "Administrator" : "Member"}
              </small>
            </div>
            <button
              aria-label="Sign out"
              title="Sign out"
              onClick={() => signOut()}
            >
              ↪
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="mobile-toggle secondary"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            ☰ <span>Menu</span>
          </button>
          <span className="topbar-location">
            Workspace <span>/</span>{" "}
            <strong>
              {navigation.find((item) => item.id === page)?.label}
            </strong>
          </span>
          <div className="topbar-right">
            <span className="session-label">
              {session.mode === "admin"
                ? "Admin workspace"
                : "Member workspace"}
            </span>
            <span className="avatar" aria-label={session.name}>
              {session.name.slice(0, 1)}
            </span>
          </div>
        </header>
        <main
          ref={main}
          id="main-content"
          tabIndex={-1}
          className="main-content"
        >
          {organization.loading ? (
            <p className="loading" role="status">
              Opening your workspace…
            </p>
          ) : organization.error ? (
            <ErrorState
              message={organization.error}
              retry={organization.reload}
            />
          ) : (
            organization.data && (
              <>
                {page === "overview" && (
                  <Overview
                    session={session}
                    organization={organization.data}
                    navigate={navigate}
                  />
                )}{" "}
                {page === "people" && <Directory call={call} />}{" "}
                {page === "structure" && (
                  <Structure call={call} organization={organization.data} />
                )}{" "}
                {page === "roles" && <Roles call={call} />}{" "}
                {page === "settings" && (
                  <Settings
                    session={session}
                    organization={organization.data}
                    call={call}
                    reload={organization.reload}
                  />
                )}
              </>
            )
          )}
        </main>
        <footer className="workspace-footer">
          NexaWork <span>A workspace that brings people together.</span>
        </footer>
      </div>
    </div>
  );
}
export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [message, setMessage] = useState("");
  const [path, setPath] = useState(window.location.pathname);
  const view = publicView(path);
  useEffect(() => {
    const handlePop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);
  useEffect(() => {
    if (view === "workspace" && !session) {
      window.history.replaceState(null, "", "/sign-in");
      setPath("/sign-in");
    }
    if (view === "login") document.title = "Sign In · NexaWork";
    if (view === "onboard") document.title = "Create Your Workspace · NexaWork";
  }, [view, session]);
  const signOut = useCallback((notice = "") => {
    setSession(null);
    setMessage(notice);
    window.history.replaceState(null, "", "/sign-in");
    setPath("/sign-in");
  }, []);
  function signIn(nextSession: Session) {
    setSession(nextSession);
    window.history.replaceState(null, "", "/workspace");
    setPath("/workspace");
    window.scrollTo(0, 0);
  }
  if (view === "landing") return <Landing />;
  if (view === "workspace" && session)
    return <Workspace session={session} signOut={signOut} />;
  if (view === "not-found")
    return (
      <main className="landing-not-found">
        <h1>Page not found.</h1>
        <p>This page is not part of your workspace.</p>
        <a href="/">Back to NexaWork</a>
      </main>
    );
  return (
    <Auth
      key={view}
      onLogin={signIn}
      message={message}
      initialView={view === "onboard" ? "onboard" : "login"}
    />
  );
}
