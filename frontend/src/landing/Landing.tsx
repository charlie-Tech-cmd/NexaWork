import { useEffect, useRef, useState } from "react";
import { Wordmark } from "../Wordmark";
import { Icon } from "../Icon";
import { navigation, features } from "./content";
import { DemoConversation } from "./DemoConversation";
import "./landing.css";

function StartLink({ light = false }: { light?: boolean }) {
  return (
    <a
      className={`landing-button ${light ? "landing-button-light" : ""}`}
      href="/get-started"
    >
      Get started <Icon name="arrow" />
    </a>
  );
}
function ConferencePhoto() {
  const [failed, setFailed] = useState(false);
  return failed ? (
    <div
      className="photo-fallback"
      role="img"
      aria-label="Conference illustration unavailable"
    >
      <Icon name="people" />
      <span>Good work starts with people.</span>
    </div>
  ) : (
    <img
      src="/images/conference-1440.webp"
      srcSet="/images/conference-720.webp 720w, /images/conference-1440.webp 1440w"
      sizes="(max-width: 1240px) calc(100vw - 40px), 1192px"
      width="1440"
      height="810"
      fetchPriority="high"
      decoding="async"
      alt="Illustration of six colleagues with varied skin tones exchanging ideas around a conference table in a bright office."
      onError={() => setFailed(true)}
    />
  );
}
function Navigation() {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const header = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
      }
    }
    function outside(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !header.current?.contains(event.target)
      )
        setOpen(false);
    }
    document.addEventListener("keydown", escape);
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("keydown", escape);
      document.removeEventListener("pointerdown", outside);
    };
  }, [open]);
  return (
    <header ref={header} className="landing-header">
      <div className="landing-container landing-nav">
        <Wordmark className="landing-wordmark" />
        <button
          ref={toggle}
          className="landing-menu-toggle"
          aria-expanded={open}
          aria-controls="landing-navigation"
          onClick={() => setOpen(!open)}
        >
          {open ? "Close" : "Menu"}
          <span aria-hidden="true">{open ? "×" : "+"}</span>
        </button>
        <nav
          id="landing-navigation"
          className={open ? "is-open" : ""}
          aria-label="Main navigation"
        >
          {navigation.map((item) => (
            <a key={item.href} href={item.href} onClick={() => setOpen(false)}>
              {item.label}
            </a>
          ))}
          <div className="landing-nav-actions">
            <a href="/sign-in" className="landing-sign-in">
              Sign in
            </a>
            <StartLink />
          </div>
        </nav>
      </div>
    </header>
  );
}
function Hero() {
  return (
    <section
      className="landing-container landing-hero"
      aria-labelledby="hero-title"
    >
      <div className="hero-copy">
        <a className="hero-announcement" href="#product">
          <span>New</span> Meet messages & private files <Icon name="arrow" />
        </a>
        <h1 id="hero-title">
          Great work.
          <br />
          <em>Better together.</em>
        </h1>
        <p className="hero-description">
          A shared space for your people, conversations, and files.
          <br className="wide-only" /> Less distance between your team and its
          next great idea.
        </p>
        <div className="hero-actions">
          <StartLink />
          <a className="landing-text-link" href="#product">
            Explore the workspace <Icon name="arrow" />
          </a>
        </div>
      </div>
      <figure className="hero-conference">
        <ConferencePhoto />
        <figcaption>
          <span>Built around people. Designed for connection.</span>
          <span>Illustrative scene</span>
        </figcaption>
      </figure>
      <div className="hero-footnote">
        <span>ONE WORKSPACE. A SHARED WAY FORWARD.</span>
        <div>
          <span>
            <Icon name="message" /> Team messaging
          </span>
          <span>
            <Icon name="file" /> Private files
          </span>
          <span>
            <Icon name="people" /> Your organization
          </span>
        </div>
      </div>
    </section>
  );
}
const sampleFiles = [
  {
    name: "Launch brief.pdf",
    size: "2.4 MB",
    person: "Amara Okafor",
    date: "Today",
  },
  {
    name: "Review notes.docx",
    size: "184 KB",
    person: "Alex Morgan",
    date: "Yesterday",
  },
  {
    name: "Project timeline.xlsx",
    size: "96 KB",
    person: "Riya Shah",
    date: "Yesterday",
  },
];
function WorkspacePreview() {
  const [tab, setTab] = useState<"messages" | "files">("messages");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  return (
    <figure className="workspace-demo">
      <div className="demo-window-bar">
        <span className="window-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span>NexaWork / Acme studio</span>
        <span>Product preview</span>
      </div>
      <div className="demo-layout">
        <aside className="demo-sidebar" aria-label="Sample workspace context">
          <div className="demo-org">
            <span>A</span>
            <div>
              Acme studio<small>Sample workspace</small>
            </div>
          </div>
          <div className="demo-nav-item">
            <Icon name="overview" /> Overview
          </div>
          <div className="demo-nav-item">
            <Icon name="people" /> People
          </div>
          <div className="demo-nav-item demo-nav-current">
            <Icon name="message" /> Messages <span>2</span>
          </div>
          <p className="demo-sidebar-label">CONVERSATIONS</p>
          <div className="demo-channel demo-channel-current">
            <span className="demo-hash">#</span>
            <div>
              Launch team<small>Let’s bring it together.</small>
            </div>
          </div>
          <div className="demo-channel">
            <span className="demo-avatar avatar-blue">AM</span>
            <div>
              Alex Morgan<small>Thanks for the update.</small>
            </div>
          </div>
          <div className="demo-user">
            <span className="demo-avatar avatar-blue">YO</span>
            <span>
              Your workspace<small>Connected by purpose</small>
            </span>
          </div>
        </aside>
        <div className="demo-main">
          <div className="demo-conversation-header">
            <div>
              <h3>Launch team</h3>
              <p>Amara, Alex, Riya and you</p>
            </div>
            <span className="demo-member-count">
              <Icon name="people" /> 4 members
            </span>
          </div>
          <div
            className="demo-tabs"
            role="tablist"
            aria-label="Explore the product preview"
          >
            {(["messages", "files"] as const).map((value, index) => (
              <button
                key={value}
                ref={(el) => {
                  tabs.current[index] = el;
                }}
                role="tab"
                id={`preview-tab-${value}`}
                aria-controls={`preview-panel-${value}`}
                aria-selected={tab === value}
                tabIndex={tab === value ? 0 : -1}
                onClick={() => setTab(value)}
                onKeyDown={(event) => {
                  if (
                    !["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                      event.key,
                    )
                  )
                    return;
                  event.preventDefault();
                  const next =
                    event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? 1
                        : 1 - index;
                  setTab(next === 0 ? "messages" : "files");
                  tabs.current[next]?.focus();
                }}
              >
                <Icon name={value === "messages" ? "message" : "file"} />
                {value === "messages" ? "Messages" : "Files"}
                {value === "files" && <span>3</span>}
              </button>
            ))}
          </div>
          <div
            id="preview-panel-messages"
            role="tabpanel"
            aria-labelledby="preview-tab-messages"
            hidden={tab !== "messages"}
            tabIndex={0}
            className="demo-panel"
          >
            <DemoConversation active={tab === "messages"} />
          </div>
          <div
            id="preview-panel-files"
            role="tabpanel"
            aria-labelledby="preview-tab-files"
            hidden={tab !== "files"}
            tabIndex={0}
            className="demo-panel demo-files-panel"
          >
            <div className="demo-files-heading">
              <h4>Shared in this conversation</h4>
              <p>The documents. The discussion. Together.</p>
            </div>
            <div className="demo-file-list">
              {sampleFiles.map((file) => (
                <div className="demo-file-row" key={file.name}>
                  <span className="preview-file-icon">
                    <Icon name="file" />
                  </span>
                  <div>
                    <strong>{file.name}</strong>
                    <span>
                      {file.person} · {file.size}
                    </span>
                  </div>
                  <span>{file.date}</span>
                </div>
              ))}
            </div>
            <p className="demo-privacy">
              <Icon name="shield" /> Available to members of this conversation.
            </p>
          </div>
        </div>
      </div>
      <figcaption>
        <span>Interactive preview · fictional people and sample content</span>
        <span>
          Send a demo message or explore Files <Icon name="arrow" />
        </span>
      </figcaption>
    </figure>
  );
}
function Product() {
  return (
    <section
      id="product"
      className="landing-container landing-section product-section"
    >
      <div className="landing-section-heading">
        <div>
          <p className="landing-eyebrow">A LITTLE LESS FRICTION</p>
          <h2>
            Keep the conversation.
            <br />
            <span>Keep the context.</span>
          </h2>
        </div>
        <p className="landing-copy">
          From a quick hello to the document that moves a project forward. Give
          your team one place to pick up where it left off.
        </p>
      </div>
      <WorkspacePreview />
      <div id="features" className="feature-pair">
        <article>
          <p className="feature-kicker">
            <Icon name="message" /> 01 / MESSAGING <span>Available now</span>
          </p>
          <h3>
            The right people.
            <br />
            The same conversation.
          </h3>
          <p>
            Start a direct conversation or bring your team into a group. Share
            an update, revisit earlier messages, and keep the work moving.
          </p>
          <a className="landing-text-link" href="/sign-in">
            Start a conversation <Icon name="arrow" />
          </a>
        </article>
        <article>
          <p className="feature-kicker">
            <Icon name="file" /> 02 / PRIVATE FILES <span>When enabled</span>
          </p>
          <h3>
            Files with a place.
            <br />
            And a little more context.
          </h3>
          <p>
            Share a document alongside your message. Find it again in the
            conversation’s Files tab, with downloads limited to its members.
          </p>
          <p className="feature-note">
            <Icon name="shield" /> Your administrator must enable file sharing
            first.
          </p>
        </article>
      </div>
    </section>
  );
}
function Organization() {
  return (
    <section id="about" className="organization-section">
      <div className="landing-container landing-section">
        <div className="landing-section-heading">
          <div>
            <p className="landing-eyebrow">CONNECTED, BY DESIGN</p>
            <h2>
              One organization.
              <br />
              <span>Room for everyone.</span>
            </h2>
          </div>
          <p className="landing-copy">
            Good collaboration starts with belonging. Build a workspace that
            reflects your people and the way your organization works.
          </p>
        </div>
        <div className="organization-layout">
          <div
            className="org-diagram"
            role="img"
            aria-label="Example organization: Acme studio contains Product with Design and Engineering, and Operations with People and culture and Finance."
          >
            <span className="diagram-label">YOUR ORGANIZATION, IN FOCUS</span>
            <div className="org-node org-root">
              <span className="org-mark">A</span>
              <div>
                Acme studio<small>One shared workspace</small>
              </div>
              <Icon name="building" />
            </div>
            <div className="org-branches">
              <div className="org-branch">
                <div className="org-node">
                  <Icon name="people" /> Product
                </div>
                <div className="org-team">Design</div>
                <div className="org-team">Engineering</div>
              </div>
              <div className="org-branch">
                <div className="org-node">
                  <Icon name="structure" /> Operations
                </div>
                <div className="org-team">People & culture</div>
                <div className="org-team">Finance</div>
              </div>
            </div>
            <span className="diagram-caption">Illustrative organization</span>
          </div>
          <div className="organization-points">
            {[
              {
                icon: "people" as const,
                title: "People, at the center.",
                text: "Add colleagues and manage employee profiles in your shared workspace.",
              },
              {
                icon: "structure" as const,
                title: "Structure that feels familiar.",
                text: "Bring regions, branches, departments, and teams into one organization.",
              },
              {
                icon: "shield" as const,
                title: "Access with intention.",
                text: "Create roles and inspect permissions to support the way your organization is managed.",
              },
            ].map((item) => (
              <article key={item.title}>
                <Icon name={item.icon} />
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
function Roadmap() {
  return (
    <section className="landing-container roadmap-section">
      <div>
        <p className="landing-eyebrow">LOOKING AHEAD</p>
        <h2>More ways to work together.</h2>
        <p>On the roadmap. Not available yet.</p>
      </div>
      <ul>
        {features
          .filter((feature) => feature.status === "Planned")
          .map((feature) => (
            <li key={feature.title}>
              <Icon name={feature.icon} />
              <span>{feature.title}</span>
              <span>Planned</span>
            </li>
          ))}
      </ul>
    </section>
  );
}
function Closing() {
  return (
    <section className="closing-section">
      <div className="landing-container">
        <p className="landing-eyebrow">YOUR PEOPLE. YOUR NEXT CHAPTER.</p>
        <h2>
          Bring it all
          <br />
          <span>together.</span>
        </h2>
        <p>A shared space. A more connected workday.</p>
        <StartLink light />
        <a href="/sign-in" className="closing-sign-in">
          Already have a workspace?{" "}
          <span>
            Sign in <Icon name="arrow" />
          </span>
        </a>
      </div>
    </section>
  );
}
function Footer() {
  return (
    <footer className="landing-footer">
      <div className="landing-container">
        <div className="footer-top">
          <div>
            <Wordmark className="landing-wordmark" />
            <p>Good work starts with connection.</p>
          </div>
          <nav aria-label="Footer product links">
            <a href="#product">Product</a>
            <a href="#features">Features</a>
            <a href="#about">About</a>
          </nav>
          <div id="contact">
            <h3>Stay connected</h3>
            <p>
              Need help with your workspace?
              <br />
              Contact your organization administrator.
            </p>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} NexaWork</span>
          <span>Conference image is an AI-generated illustration.</span>
          <a href="/sign-in">
            Your workspace <Icon name="arrow" />
          </a>
        </div>
      </div>
    </footer>
  );
}
export default function Landing() {
  useEffect(() => {
    document.title = "NexaWork — Great work. Better together.";
  }, []);
  return (
    <div className="landing-page">
      <a className="landing-skip" href="#landing-main">
        Skip to content
      </a>
      <Navigation />
      <main id="landing-main" tabIndex={-1}>
        <Hero />
        <Product />
        <Organization />
        <Roadmap />
        <Closing />
      </main>
      <Footer />
    </div>
  );
}
