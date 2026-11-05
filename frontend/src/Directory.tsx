import { useState, type FormEvent } from "react";
import { errorMessage, record, records, type RecordData } from "./api";
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
type InvitationBranch = {
  id: number;
  name: string;
  regionName: string;
  departments: { id: number; name: string }[];
};

async function loadPages(
  call: Call,
  path: string,
  signal: AbortSignal,
): Promise<RecordData[]> {
  const result: RecordData[] = [];
  let offset = 0;
  while (true) {
    const page = records(
      await call(
        `${path}?limit=100&offset=${offset}`,
        "GET",
        undefined,
        signal,
      ),
    );
    result.push(...page);
    if (page.length < 100) return result;
    offset += page.length;
  }
}

async function loadInvitationBranches(
  call: Call,
  organizationId: number,
  signal: AbortSignal,
): Promise<InvitationBranch[]> {
  const regions = await loadPages(
    call,
    `/regions/organizations/${organizationId}`,
    signal,
  );
  const branchGroups = await Promise.all(
    regions
      .filter((region) => region.is_active !== false)
      .map(async (region) => ({
        regionName: String(region.name),
        branches: await loadPages(
          call,
          `/branches/regions/${region.id}`,
          signal,
        ),
      })),
  );
  const branches = branchGroups.flatMap(({ regionName, branches }) =>
    branches
      .filter((branch) => branch.is_active !== false)
      .map((branch) => ({ branch, regionName })),
  );
  return (
    await Promise.all(
      branches.map(async ({ branch, regionName }) => ({
        id: branch.id,
        name: String(branch.name),
        regionName,
        departments: (
          await loadPages(call, `/departments/branches/${branch.id}`, signal)
        )
          .filter((department) => department.is_active !== false)
          .map((department) => ({
            id: department.id,
            name: String(department.name),
          })),
      })),
    )
  ).filter((branch) => branch.departments.length > 0);
}

function InvitePersonForm({
  call,
  branches,
  onCancel,
  onCreated,
}: {
  call: Call;
  branches: InvitationBranch[];
  onCancel: () => void;
  onCreated: (invitation: RecordData) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [branchId, setBranchId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const selectedBranch = branches.find(
    (branch) => String(branch.id) === branchId,
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    const data = Object.fromEntries(
      new FormData(event.currentTarget),
    ) as Record<string, string>;
    try {
      const invitation = record(
        await call("/onboarding/invitations", "POST", {
          full_name: data.full_name,
          email: data.email,
          job_title: data.job_title,
          branch_id: Number(branchId),
          department_id: Number(departmentId),
        }),
      );
      if (typeof invitation.acceptance_url !== "string") {
        throw new Error("The server did not return an invitation link.");
      }
      onCreated(invitation);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel editor">
      <h2>Invite a person</h2>
      <p className="muted">
        They’ll choose their own password when they accept the invitation.
      </p>
      {branches.length === 0 ? (
        <p className="notice">
          Add an active branch and department under Organization before inviting
          people.
        </p>
      ) : (
        <form className="data-form" onSubmit={submit}>
          <fieldset disabled={busy}>
            {personFields.map((field) => (
              <label key={field.name}>
                {field.label}
                <input
                  name={field.name}
                  type={field.type || "text"}
                  required
                  minLength={field.minLength}
                  maxLength={255}
                  autoComplete={field.type === "email" ? "email" : "name"}
                />
              </label>
            ))}
            <label>
              Job title
              <input name="job_title" required minLength={2} maxLength={255} />
            </label>
            <label>
              Branch
              <select
                required
                value={branchId}
                onChange={(event) => {
                  setBranchId(event.target.value);
                  setDepartmentId("");
                }}
              >
                <option value="">Choose a branch</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.regionName} / {branch.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Department
              <select
                required
                value={departmentId}
                onChange={(event) => setDepartmentId(event.target.value)}
                disabled={!selectedBranch}
              >
                <option value="">Choose a department</option>
                {selectedBranch?.departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </label>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <div className="form-actions">
              <button className="primary" type="submit">
                {busy ? "Creating invitation…" : "Create invitation"}
              </button>
              <button className="secondary" type="button" onClick={onCancel}>
                Cancel
              </button>
            </div>
          </fieldset>
        </form>
      )}
      {branches.length === 0 && (
        <button className="secondary" onClick={onCancel}>
          Close
        </button>
      )}
    </section>
  );
}

export function InvitationLink({ invitation }: { invitation: RecordData }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const url = String(invitation.acceptance_url);

  async function copyLink() {
    setError("");
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
      setError("Copy was unavailable. Select and copy the invitation link.");
    }
  }

  return (
    <section className="panel editor">
      <h2>Invitation ready</h2>
      <p className="muted">
        Email delivery is simulated in this development setup. Share this
        one-time link securely so they can choose their password.
      </p>
      <label className="invitation-link-field">
        Invitation link
        <input
          readOnly
          value={url}
          onFocus={(event) => event.target.select()}
        />
      </label>
      <div className="form-actions">
        <button className="primary" type="button" onClick={copyLink}>
          {copied ? "Copied" : "Copy invitation link"}
        </button>
        <a className="secondary invitation-open-link" href={url}>
          Open invitation
        </a>
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

export function Directory({
  call,
  organizationId,
  canInvite,
}: {
  call: Call;
  organizationId: number;
  canInvite: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<RecordData | null>(null);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [lastInvitation, setLastInvitation] = useState<RecordData | null>(null);
  const [notice, setNotice] = useState("");
  const inviteLocations = useResource(
    (signal) =>
      showInviteForm
        ? loadInvitationBranches(call, organizationId, signal)
        : Promise.resolve([]),
    [call, organizationId, showInviteForm],
  );
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
  const fields = personFields.map((field) => ({
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
        {canInvite && (
          <button
            className="primary"
            onClick={() => {
              setEditing(null);
              setLastInvitation(null);
              setShowInviteForm(true);
              setNotice("");
            }}
          >
            + Invite person
          </button>
        )}
      </PageHeading>
      {notice && (
        <p role="status" className="notice success">
          {notice}
        </p>
      )}
      {editing && (
        <section className="panel editor">
          <h2>Edit person</h2>
          <p className="muted">Update their workspace profile.</p>
          <DataForm
            key={editing.id}
            fields={fields}
            submit="Save changes"
            onCancel={() => setEditing(null)}
            onSave={async (data) => {
              await call(`/users/${editing.id}`, "PUT", data);
              setEditing(null);
              setNotice("Person updated.");
              resource.reload();
            }}
          />
        </section>
      )}
      {showInviteForm &&
        (inviteLocations.loading ? (
          <section className="panel editor">
            <p className="loading" role="status">
              Loading organization locations…
            </p>
          </section>
        ) : inviteLocations.error ? (
          <section className="panel editor">
            <ErrorState
              message={inviteLocations.error}
              retry={inviteLocations.reload}
            />
            <button
              className="secondary"
              onClick={() => setShowInviteForm(false)}
            >
              Close
            </button>
          </section>
        ) : (
          <InvitePersonForm
            call={call}
            branches={inviteLocations.data || []}
            onCancel={() => setShowInviteForm(false)}
            onCreated={(invitation) => {
              setShowInviteForm(false);
              setLastInvitation(invitation);
              setNotice("Invitation created.");
            }}
          />
        ))}
      {lastInvitation && <InvitationLink invitation={lastInvitation} />}
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
          <div
            className="table-scroll"
            role="region"
            aria-label="People directory table"
            tabIndex={0}
          >
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
                : "Invite a person to help your organization get started."
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
