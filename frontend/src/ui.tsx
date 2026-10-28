import { Icon } from "./Icon";
import { useState, type FormEvent, type ReactNode } from "react";
import { errorMessage } from "./api";
export type Field = {
  name: string;
  label: string;
  type?: string;
  value?: string;
  minLength?: number;
  maxLength?: number;
  optional?: boolean;
  options?: { value: string; label: string }[];
};
export function DataForm({
  fields,
  submit,
  onSave,
  onCancel,
}: {
  fields: Field[];
  submit: string;
  onSave: (data: Record<string, string>) => Promise<void>;
  onCancel?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [visiblePasswords, setVisiblePasswords] = useState<
    Record<string, boolean>
  >({});
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = Object.fromEntries(
      new FormData(event.currentTarget),
    ) as Record<string, string>;
    const password = data.password || data.admin_password;
    const confirmation = data.confirm_password || data.admin_confirm_password;
    if (confirmation !== undefined && password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onSave(data);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={save} className="data-form">
      <fieldset disabled={busy}>
        {fields.map((field) => {
          const isPassword = field.type === "password";
          const visible = Boolean(visiblePasswords[field.name]);
          const input = (
            <input
              name={field.name}
              type={isPassword && visible ? "text" : field.type || "text"}
              defaultValue={field.value || ""}
              required={!field.optional}
              minLength={field.minLength}
              maxLength={field.maxLength || 255}
              autoComplete={
                field.type === "password"
                  ? field.name.includes("confirm") || field.minLength
                    ? "new-password"
                    : "current-password"
                  : field.type === "email"
                    ? "email"
                    : "off"
              }
            />
          );

          return (
            <label key={field.name}>
              {field.label}
              {field.optional && <span className="muted"> (optional)</span>}
              {field.options ? (
                <select
                  name={field.name}
                  defaultValue={field.value}
                  required={!field.optional}
                >
                  {field.options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : isPassword ? (
                <span className="password-input">
                  {input}
                  <button
                    className="password-toggle"
                    type="button"
                    aria-label={`${visible ? "Hide" : "Show"} ${field.label.toLowerCase()}`}
                    aria-pressed={visible}
                    onClick={() =>
                      setVisiblePasswords((current) => ({
                        ...current,
                        [field.name]: !current[field.name],
                      }))
                    }
                  >
                    <Icon name={visible ? "eye-off" : "eye"} />
                  </button>
                </span>
              ) : (
                input
              )}
            </label>
          );
        })}
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        <div className="form-actions">
          <button className="primary" type="submit">
            {busy ? "Saving…" : submit}
          </button>
          {onCancel && (
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
          )}
        </div>
      </fieldset>
    </form>
  );
}
export function Status({ active }: { active: unknown }) {
  return (
    <span className={`status ${active ? "" : "inactive"}`}>
      <span aria-hidden="true">●</span> {active ? "Active" : "Inactive"}
    </span>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {children}
    </header>
  );
}
export function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <span className="empty-symbol" aria-hidden="true">
        <Icon name="structure" />
      </span>
      <h3>{title}</h3>
      <p className="muted">{text}</p>
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="notice error" role="alert">
      <p>{message}</p>
      <button className="secondary" onClick={retry}>
        Try again
      </button>
    </div>
  );
}
