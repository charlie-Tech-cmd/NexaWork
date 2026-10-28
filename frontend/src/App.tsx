import { Wordmark } from "./Wordmark";
import { Icon, type IconName } from "./Icon";
import Landing from "./landing/Landing";
import { publicView, resetTokenFromSearch } from "./landing/content";
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
const navigation: { id: string; label: string; icon: IconName }[] = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "people", label: "People", icon: "people" },
  { id: "structure", label: "Organization", icon: "structure" },
  { id: "roles", label: "Roles & access", icon: "shield" },
  { id: "settings", label: "Settings", icon: "settings" },
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
            Explore your organization <Icon name="arrow" />
          </button>
        </div>
        <div className="workspace-art" aria-hidden="true">
          <span className="art-label">{String(organization.name)}</span>
          <div className="art-line" />
          <div className="art-nodes">
            <span>
              <Icon name="globe" />
            </span>
            <span>
              <Icon name="building" />
            </span>
            <span>
              <Icon name="people" />
            </span>
          </div>
          <div className="art-caption">A connected workspace</div>
        </div>
      </section>
      <div className="section-heading">
        <h2>Your everyday essentials</h2>
        <span className="muted">A good place to start</span>
      </div>
      <div className="quick-grid">
        {(
          [
            {
              page: "people",
              icon: "people",
              name: "Bring people together",
              text: "Find a colleague or add someone new.",
              action: "Open directory",
            },
            {
              page: "structure",
              icon: "structure",
              name: "See the bigger picture",
              text: "Explore regions, branches, departments and teams.",
              action: "Explore organization",
            },
            {
              page: "roles",
              icon: "shield",
              name: "Make access clear",
              text: "See workspace roles and their permissions.",
              action: "View roles",
            },
          ] satisfies {
            page: string;
            icon: IconName;
            name: string;
            text: string;
            action: string;
          }[]
        ).map((item) => (
          <button
            className="quick-card"
            key={item.page}
            onClick={() => navigate(item.page)}
          >
            <span className="structure-icon" aria-hidden="true">
              <Icon name={item.icon} />
            </span>
            <h3>{item.name}</h3>
            <p className="muted">{item.text}</p>
            <span className="card-link">
              {item.action} <Icon name="arrow" />
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
  notice,
  onSaved,
  session,
}: {
  organization: RecordData;
  call: Call;
  notice: string;
  onSaved: () => void;
  session: Session;
}) {
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
            <p className="notice success" role="status">
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
              onSaved();
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
  const [settingsNotice, setSettingsNotice] = useState("");
  const main = useRef<HTMLElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const menuToggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menu) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenu(false);
        menuToggle.current?.focus();
      }
    }
    function closeOutside(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !sidebar.current?.contains(event.target) &&
        !menuToggle.current?.contains(event.target)
      )
        setMenu(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOutside);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOutside);
    };
  }, [menu]);
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
    setSettingsNotice("");
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
      <aside
        ref={sidebar}
        id="workspace-sidebar"
        className={`sidebar ${menu ? "open" : ""}`}
      >
        <Wordmark
          inverse
          href="#overview"
          label="NexaWork workspace overview"
          onClick={(event) => {
            event.preventDefault();
            navigate("overview");
          }}
        />
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
              <span aria-hidden="true">
                <Icon name={item.icon} />
              </span>
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
            <span aria-hidden="true">
              <Icon name="people" />
            </span>
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
              <Icon name="logout" />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            ref={menuToggle}
            className="mobile-toggle secondary"
            aria-controls="workspace-sidebar"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Icon name="menu" /> <span>Menu</span>
          </button>
          <span className="topbar-location">
            Workspace <span>/</span>{" "}
            <strong>
              {navigation.find((item) => item.id === page)?.label}
            </strong>
          </span>
          <div className="topbar-right">
            <Wordmark
              className="mobile-wordmark"
              href="#overview"
              label="NexaWork workspace overview"
              onClick={(event) => {
                event.preventDefault();
                navigate("overview");
              }}
            />
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
                    notice={settingsNotice}
                    onSaved={() => {
                      setSettingsNotice("Organization updated.");
                      organization.reload();
                    }}
                  />
                )}
              </>
            )
          )}
        </main>
        <footer className="workspace-footer">
          NexaWork <span>Connect. Collaborate. Work Smarter.</span>
        </footer>
      </div>
    </div>
  );
}
export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [message, setMessage] = useState("");
  const [path, setPath] = useState(window.location.pathname);
  const [resetToken] = useState(() =>
    resetTokenFromSearch(window.location.search),
  );
  const view = publicView(path);
  useEffect(() => {
    const handlePop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);
  useEffect(() => {
    if (
      view === "reset" &&
      new URLSearchParams(window.location.search).has("token")
    ) {
      const url = new URL(window.location.href);
      url.searchParams.delete("token");
      window.history.replaceState(
        null,
        "",
        `${url.pathname}${url.search}${url.hash}`,
      );
    }
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
        <Wordmark />
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
      onResetSuccess={() => {
        setMessage("Password updated. Sign in with your new password.");
        window.history.replaceState(null, "", "/sign-in");
        setPath("/sign-in");
      }}
      initialView={
        view === "onboard" ? "onboard" : view === "reset" ? "reset" : "login"
      }
      initialToken={view === "reset" ? resetToken : ""}
    />
  );
}
