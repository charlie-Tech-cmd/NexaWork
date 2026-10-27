import { Wordmark } from "./Wordmark";
import { useState } from "react";
import { request, loginSession, type Session } from "./api";
import { DataForm, type Field } from "./ui";
const password: Field = {
  name: "password",
  label: "Password",
  type: "password",
};
export function Auth({
  onLogin,
  message,
  initialView = "login",
}: {
  onLogin: (session: Session) => void;
  message: string;
  initialView?: "login" | "onboard";
}) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const [view, setView] = useState(initialView as string);
  const [mode, setMode] = useState("member");
  const [notice, setNotice] = useState(message);
  const onboarding: Field[] = [
    { name: "organization_name", label: "Organization name", minLength: 2 },
    {
      name: "organization_slug",
      label: "Organization handle",
      minLength: 2,
      maxLength: 100,
    },
    { name: "admin_full_name", label: "Your full name", minLength: 2 },
    { name: "admin_email", label: "Work email", type: "email" },
    {
      name: "admin_password",
      label: "Password (12 characters minimum)",
      type: "password",
      minLength: 12,
    },
    {
      name: "admin_confirm_password",
      label: "Confirm password",
      type: "password",
    },
  ];
  const fields =
    view === "onboard"
      ? onboarding
      : view === "recover"
        ? [{ name: "email", label: "Work email", type: "email" }]
        : view === "reset"
          ? [
              { name: "token", label: "Reset token" },
              {
                name: "new_password",
                label: "New password (12 characters minimum)",
                type: "password",
                minLength: 12,
              },
            ]
          : [
              mode === "employee"
                ? { name: "employee_id", label: "Employee ID" }
                : { name: "email", label: "Work email", type: "email" },
              password,
            ];
  const title =
    view === "onboard"
      ? "Make room for your team."
      : view === "recover"
        ? "Find your way back."
        : view === "reset"
          ? "A fresh start."
          : "Welcome back.";
  async function submit(data: Record<string, string>) {
    if (view === "onboard") {
      await request("/organizations/onboard", "", "POST", data);
      setNotice(
        "Your workspace is ready. Sign in with your new administrator account.",
      );
      setMode("admin");
      setView("login");
    } else if (view === "recover") {
      await request("/auth/forgot-password", "", "POST", data);
      setNotice(
        "Request accepted. If recovery email is available for your account, check your inbox. Contact your administrator if it does not arrive.",
      );
    } else if (view === "reset") {
      await request("/auth/reset-password", "", "POST", data);
      setNotice("Password updated. Sign in with your new password.");
      setView("login");
    } else {
      const path = mode === "member" ? "/auth/login" : `/auth/${mode}/login`;
      onLogin(loginSession(await request(path, "", "POST", data), mode));
    }
  }
  function change(next: string) {
    setView(next);
    setNotice("");
  }
  return (
    <main className="auth-layout">
      <section className="auth-story">
        <Wordmark inverse />
        <div>
          <p className="eyebrow">A PLACE TO WORK TOGETHER</p>
          <h2>
            One workspace.
            <br />
            Every part
            <br />
            of your team.
          </h2>
          <p>
            Bring your people and organization together.
            <br />A clearer way to manage the everyday.
          </p>
          <figure className="auth-photo">
            {!photoFailed && (
              <img
                src="/images/team-office-720.jpg"
                width="720"
                height="405"
                alt="Colleagues collaborating around a table in a bright office"
                loading="lazy"
                onError={() => setPhotoFailed(true)}
              />
            )}
            <figcaption>A shared space. A stronger team.</figcaption>
          </figure>
        </div>
        <p className="auth-footer">Connect. Collaborate. Work Smarter.</p>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <a className="auth-home-link" href="/">
            ← Back to NexaWork
          </a>
          <p className="eyebrow">YOUR NEXAWORK WORKSPACE</p>
          <h1>{title}</h1>
          <p className="muted">
            {view === "login"
              ? "Sign in to pick up where you left off."
              : view === "onboard"
                ? "Start with your organization and its first administrator."
                : "Recover access to your workspace."}
          </p>
          {view === "login" && (
            <div className="segmented" aria-label="Sign-in type">
              {["member", "admin", "employee"].map((item) => (
                <button
                  key={item}
                  aria-pressed={mode === item}
                  onClick={() => setMode(item)}
                >
                  {item === "admin"
                    ? "Administrator"
                    : item === "employee"
                      ? "Employee ID"
                      : "Member"}
                </button>
              ))}
            </div>
          )}
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          <DataForm
            key={`${view}-${mode}`}
            fields={fields}
            submit={
              view === "login"
                ? "Sign in to workspace →"
                : view === "onboard"
                  ? "Create workspace →"
                  : view === "recover"
                    ? "Request recovery"
                    : "Update password"
            }
            onSave={submit}
          />
          <div className="auth-links">
            {view === "login" ? (
              <>
                <button onClick={() => change("recover")}>
                  Forgot password?
                </button>
                <p>
                  New to NexaWork?{" "}
                  <button onClick={() => change("onboard")}>
                    Create a workspace
                  </button>
                </p>
              </>
            ) : (
              <>
                <button onClick={() => change("login")}>
                  ← Back to sign in
                </button>
                {view === "recover" && (
                  <button onClick={() => change("reset")}>
                    I have a reset token
                  </button>
                )}
              </>
            )}
          </div>
          <p className="session-note">
            For your privacy, refreshing this page signs you out.
          </p>
        </div>
      </section>
    </main>
  );
}
