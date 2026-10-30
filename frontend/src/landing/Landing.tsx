import { useEffect, useRef, useState } from "react";
import { Wordmark } from "../Wordmark";
import { Icon } from "../Icon";
import { dayScenes, navigation, features } from "./content";
import "./landing.css";
function StartLink({ className = "" }: { className?: string }) {
  return (
    <a className={`landing-button ${className}`} href="/get-started">
      Get Started <Icon name="arrow" />
    </a>
  );
}
function OfficePhoto({
  kind,
  priority = false,
}: {
  kind: "team-office" | "office-collaboration";
  priority?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  return failed ? (
    <div
      className="photo-fallback"
      role="img"
      aria-label="Office collaboration photograph unavailable"
    >
      <Icon name="people" />
      <span>Good work starts with people.</span>
    </div>
  ) : (
    <img
      src={`/images/${kind}-1440.jpg`}
      srcSet={`/images/${kind}-720.jpg 720w, /images/${kind}-1440.jpg 1440w`}
      sizes="(max-width: 720px) 100vw, (max-width: 1100px) 50vw, 620px"
      width="1440"
      height={kind === "team-office" ? 810 : 961}
      alt={
        kind === "team-office"
          ? "Colleagues sharing ideas around a table with laptops in a bright contemporary office."
          : "Colleagues discussing their work around a meeting table with laptops and notebooks."
      }
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding="async"
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
          <span aria-hidden="true">{open ? "×" : "☰"}</span>
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
              Sign In
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
        <p className="landing-eyebrow">
          <span /> CONNECT. COLLABORATE. WORK SMARTER.
        </p>
        <h1 id="hero-title">
          Great Work
          <br />
          Happens When
          <br />
          <em>Teams Connect.</em>
        </h1>
        <p className="hero-description">
          Bring your people, conversations, and shared documents together.
          Message a colleague, collaborate in groups, and keep files close to
          the work they belong to.
        </p>
        <div className="hero-actions">
          <StartLink />
          <a href="#features" className="landing-button landing-button-outline">
            Explore Features <Icon name="arrow" />
          </a>
        </div>
        <p className="hero-availability">
          Team messaging is here.
          <br />
          Private file sharing is available when enabled for your workspace.
        </p>
        <div className="hero-bottom-note">
          <span className="hero-note-icon">
            <Icon name="people" />
          </span>
          <p>
            Built around people.
            <br />
            <strong>Designed for the way teams work.</strong>
          </p>
        </div>
      </div>
      <div className="hero-visual">
        <div className="hero-photo">
          <OfficePhoto kind="team-office" priority />
          <div className="photo-shade" />
          <span className="photo-label">
            <span /> BETTER, TOGETHER.
          </span>
          <p className="photo-caption">
            Every great idea
            <br />
            starts with a conversation.
          </p>
        </div>
        <div className="hero-floating-card">
          <span className="floating-icon">
            <Icon name="globe" />
          </span>
          <div>
            <span>ONE CONNECTED WORKPLACE</span>
            <strong>People. Teams. Possibilities.</strong>
          </div>
          <span className="floating-check">
            <Icon name="check" />
          </span>
        </div>
        <span className="hero-photo-index">01 / THE MODERN WORKPLACE</span>
      </div>
    </section>
  );
}
function Product() {
  const available = [
    {
      icon: "people",
      title: "Your people, in one place.",
      text: "Create your workspace, add colleagues, and manage their profiles.",
    },
    {
      icon: "channels",
      title: "Structure that makes sense.",
      text: "Bring regions, branches, departments and teams into one organization.",
    },
    {
      icon: "shield",
      title: "Access with intention.",
      text: "Use administrator sign-in, create roles, and inspect their permissions.",
    },
  ] as const;
  return (
    <section id="product" className="product-foundation landing-section">
      <div className="landing-container">
        <div className="foundation-heading">
          <div>
            <p className="landing-eyebrow">THE FOUNDATION FOR BETTER WORK</p>
            <h2>
              A shared space.
              <br />A more connected organization.
            </h2>
          </div>
          <div>
            <span className="availability-badge available">
              <span /> Available now
            </span>
            <p className="landing-copy">
              Set up your organization, bring in your people, and start the
              conversations that move work forward.
            </p>
          </div>
        </div>
        <div className="foundation-grid">
          {available.map((item, index) => (
            <article key={item.title}>
              <span className="foundation-number">0{index + 1}</span>
              <span className="landing-icon">
                <Icon name={item.icon} />
              </span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
function Features() {
  return (
    <section
      id="features"
      className="landing-container landing-section features-section"
    >
      <div className="centered-heading">
        <p className="landing-eyebrow">MESSAGES AND FILES, TOGETHER</p>
        <h2>Keep your team and its work connected.</h2>
        <p className="landing-copy">
          Direct conversations, group discussions, and private file sharing now
          join your workspace.
          <br className="wide-only" /> More ways to collaborate are on the
          roadmap, with availability shown below.
        </p>
      </div>
      <div className="landing-feature-grid">
        {features.map((feature, index) => (
          <article
            className={`landing-feature-card ${feature.status !== "Planned" ? "feature-implemented" : ""}`}
            key={feature.title}
          >
            <div className="feature-top">
              <span className={`landing-icon feature-tone-${index % 3}`}>
                <Icon name={feature.icon} />
              </span>
              <span
                className={`availability-badge ${feature.status !== "Planned" ? "available" : ""}`}
              >
                {feature.status}
              </span>
            </div>
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
          </article>
        ))}
      </div>
      <p className="feature-enablement-note">
        To share files, your workspace administrator must first enable file
        sharing. Messages and shared files stay within their conversation.
      </p>
    </section>
  );
}
function ConceptPreview({ scene }: { scene: (typeof dayScenes)[number] }) {
  return (
    <figure className="concept-preview">
      <figcaption>
        <span>
          <span className="concept-dot" /> NexaWork
        </span>
        <small>Illustrative preview · sample content</small>
      </figcaption>
      <div className="concept-title">
        <span className="landing-icon">
          <Icon name={scene.icon} />
        </span>
        <div>
          <small>
            {scene.status === "Planned"
              ? "PLANNED EXPERIENCE"
              : "WORKSPACE FEATURE"}
          </small>
          <h4>{scene.label}</h4>
        </div>
      </div>
      <div className="concept-rows">
        {scene.rows.map((row, index) => (
          <div key={row}>
            <span className={`concept-row-icon row-${index}`}>
              <Icon
                name={
                  index === 0 ? scene.icon : index === 1 ? "people" : "file"
                }
              />
            </span>
            <span>{row}</span>
            <Icon name="chevron" />
          </div>
        ))}
      </div>
    </figure>
  );
}
function Workday() {
  const [selected, setSelected] = useState(0);
  const scene = dayScenes[selected];
  return (
    <section
      className="workday-section landing-section"
      aria-labelledby="workday-title"
    >
      <div className="landing-container workday-layout">
        <div className="workday-visual">
          <div className="workday-photo">
            <OfficePhoto kind="office-collaboration" />
            <span className="workday-photo-label">
              MADE FOR EVERYDAY MOMENTS.
            </span>
          </div>
          <div id="workday-preview" aria-live="polite">
            <ConceptPreview scene={scene} />
          </div>
        </div>
        <div className="workday-copy">
          <p className="landing-eyebrow">
            FROM THE FIRST HELLO TO THE NEXT BIG IDEA
          </p>
          <h2 id="workday-title">
            A better workday
            <br />
            starts with connection.
          </h2>
          <p className="landing-copy">
            People do their best work when they have the right context, the
            right conversations, and each other.
          </p>
          <div className="workday-scenes">
            {dayScenes.map((item, index) => (
              <div
                className={`workday-scene ${selected === index ? "selected" : ""}`}
                key={item.title}
              >
                <button
                  aria-expanded={selected === index}
                  aria-controls={`scene-${index}`}
                  onClick={() => setSelected(index)}
                >
                  <span className="scene-number">0{index + 1}</span>
                  <span>{item.title}</span>
                  <span aria-hidden="true">
                    {selected === index ? "−" : "+"}
                  </span>
                </button>
                <div id={`scene-${index}`} hidden={selected !== index}>
                  <p>{item.description}</p>
                  <span
                    className={`availability-badge ${item.status !== "Planned" ? "available" : ""}`}
                  >
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
function Benefits() {
  const benefits = [
    {
      icon: "message",
      title: "Fewer walls. More conversation.",
      text: "Reach a colleague directly or bring the right people into a group conversation.",
    },
    {
      icon: "file",
      title: "Less searching. More context.",
      text: "Find shared documents alongside the messages that explain them, in each conversation’s Files tab.",
    },
    {
      icon: "people",
      title: "One team. A shared direction.",
      text: "An organization foundation that helps people see where they belong.",
    },
  ] as const;
  return (
    <section
      id="about"
      className="landing-container landing-section benefits-section"
    >
      <div className="centered-heading">
        <p className="landing-eyebrow">WORK IS BETTER WHEN WE’RE CONNECTED</p>
        <h2>
          Built for people.
          <br />
          With the whole organization in mind.
        </h2>
        <p className="landing-copy">
          Give your people a shared place to talk, exchange documents, and work
          together.
          <br className="wide-only" /> Built around your organization and the
          teams within it.
        </p>
      </div>
      <div className="benefits-grid">
        {benefits.map((item) => (
          <article key={item.title}>
            <span className="benefit-icon">
              <Icon name={item.icon} />
            </span>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
function Closing() {
  return (
    <section className="landing-container closing-section">
      <div className="closing-card">
        <div className="closing-lines" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div>
          <p className="landing-eyebrow">
            YOUR PEOPLE. YOUR WORKSPACE. TOGETHER.
          </p>
          <h2>Bring Your Team Together.</h2>
          <p>Create a more connected workplace with NexaWork.</p>
          <StartLink className="landing-button-light" />
          <small>
            Set up your workspace, add colleagues, and start a conversation.
          </small>
        </div>
        <span className="closing-symbol" aria-hidden="true">
          <Icon name="people" />
        </span>
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
            <p>Connect. Collaborate. Work Smarter.</p>
            <span>A shared foundation for the modern workplace.</span>
          </div>
          <nav aria-label="Footer product links">
            <h3>Explore NexaWork</h3>
            <a href="#product">Product</a>
            <a href="#features">Features & roadmap</a>
            <a href="#about">About</a>
          </nav>
          <nav aria-label="Workspace links">
            <h3>Your workspace</h3>
            <a href="/sign-in">Sign In</a>
            <a href="/get-started">Get Started</a>
          </nav>
          <div id="contact" className="landing-contact">
            <h3>Contact</h3>
            <p>
              Already part of a workspace?
              <br />
              Contact your organization administrator.
            </p>
            <span>A public contact channel is not available yet.</span>
          </div>
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} NexaWork. All rights reserved.
          </span>
          <span>
            Office photography:{" "}
            <a
              href="https://unsplash.com/photos/fm4B1xWEIsU"
              target="_blank"
              rel="noreferrer"
            >
              Vitaly Gariev
            </a>{" "}
            &{" "}
            <a
              href="https://www.pexels.com/photo/group-of-people-beside-table-1181433/"
              target="_blank"
              rel="noreferrer"
            >
              Christina Morillo
            </a>
          </span>
        </div>
      </div>
    </footer>
  );
}
export default function Landing() {
  useEffect(() => {
    document.title = "NexaWork — Connect. Collaborate. Work Smarter.";
  }, []);
  return (
    <div className="landing-page">
      <a className="landing-skip" href="#landing-main">
        Skip to content
      </a>
      <Navigation />
      <main id="landing-main" tabIndex={-1}>
        <Hero />
        <div className="landing-container landing-principles">
          <span>Good work starts with a shared space.</span>
          <span>
            <Icon name="people" /> People first
          </span>
          <span>
            <Icon name="channels" /> Organized by design
          </span>
          <span>
            <Icon name="globe" /> Connected by purpose
          </span>
        </div>
        <Product />
        <Features />
        <Workday />
        <Benefits />
        <Closing />
      </main>
      <Footer />
    </div>
  );
}
