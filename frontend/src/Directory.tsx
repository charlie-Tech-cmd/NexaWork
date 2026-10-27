import { useState } from "react";
import { records, type RecordData } from "./api";
import {
  DataForm,
  Empty,
  ErrorState,
  PageHeading,
  Status,
  type Field,
} from "./ui";
import { useResource } from "./useResource";
export type Call = (
  path: string,
  method?: string,
  body?: unknown,
  signal?: AbortSignal,
) => Promise<unknown>;
const personFields: Field[] = [
  { name: "full_name", label: "Full name", minLength: 2 },
  { name: "email", label: "Work email", type: "email" },
];
export function Directory({ call }: { call: Call }) {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<RecordData | "new" | null>(null);
  const [notice, setNotice] = useState("");
  const resource = useResource(
    async (signal) =>
      records(
        await call(
          `/users?limit=20&offset=${offset}`,
          "GET",
          undefined,
          signal,
        ),
      ),
    [offset],
  );
  const people =
    resource.data?.filter((person) =>
      `${person.full_name} ${person.email}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) || [];
  const fields =
    editing === "new"
      ? [
          ...personFields,
          {
            name: "password",
            label: "Temporary password (12 characters minimum)",
            type: "password",
            minLength: 12,
          },
          {
            name: "confirm_password",
            label: "Confirm password",
            type: "password",
          },
        ]
      : personFields.map((field) => ({
          ...field,
          value: String(editing?.[field.name] || ""),
        }));
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / PEOPLE"
        title="People make it work."
        description="Find and manage the people in your organization."
      >
        <button
          className="primary"
          onClick={() => {
            setEditing("new");
            setNotice("");
          }}
        >
          + Add person
        </button>
      </PageHeading>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {editing && (
        <section className="panel editor">
          <h2>{editing === "new" ? "Add a person" : "Edit person"}</h2>
          <p className="muted">
            {editing === "new"
              ? "Create an account. Share its temporary credentials through a secure channel."
              : "Update their workspace profile."}
          </p>
          <DataForm
            key={editing === "new" ? "new" : editing.id}
            fields={fields}
            submit="Save person"
            onCancel={() => setEditing(null)}
            onSave={async (data) => {
              await call(
                editing === "new" ? "/users" : `/users/${editing.id}`,
                editing === "new" ? "POST" : "PUT",
                data,
              );
              setEditing(null);
              setNotice("Person saved.");
              resource.reload();
            }}
          />
        </section>
      )}
      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>People directory</h2>
            <p className="muted">20 people per page · active accounts</p>
          </div>
          <label className="search-label">
            <span className="sr-only">Search this page</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search this page…"
            />
          </label>
        </div>
        {resource.loading ? (
          <p className="loading" role="status">
            Loading people…
          </p>
        ) : resource.error ? (
          <ErrorState message={resource.error} retry={resource.reload} />
        ) : people.length ? (
          <div className="table-scroll">
            <table>
              <caption className="sr-only">
                People in your organization, page {offset / 20 + 1}
              </caption>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email address</th>
                  <th>Status</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {people.map((person) => (
                  <tr key={person.id}>
                    <td>
                      <div className="person">
                        <span className="avatar" aria-hidden="true">
                          {String(person.full_name).slice(0, 1).toUpperCase()}
                        </span>
                        <strong>{String(person.full_name)}</strong>
                      </div>
                    </td>
                    <td>{String(person.email)}</td>
                    <td>
                      <Status active={person.is_active} />
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => setEditing(person)}
                        aria-label={`Edit ${person.full_name}`}
                      >
                        Edit ↗
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title={
              search ? "No matches on this page" : "No people on this page"
            }
            text={
              search
                ? "Try a different name or email, or browse another page."
                : "Add a person to help your organization get started."
            }
          />
        )}
        <div className="pagination">
          <span>Page {offset / 20 + 1}</span>
          <div>
            <button
              className="secondary"
              disabled={offset === 0 || resource.loading}
              onClick={() => {
                setOffset(offset - 20);
                setSearch("");
              }}
            >
              ← Previous
            </button>
            <button
              className="secondary"
              disabled={
                resource.loading ||
                !!resource.error ||
                (resource.data?.length || 0) < 20
              }
              onClick={() => {
                setOffset(offset + 20);
                setSearch("");
              }}
            >
              Next →
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
