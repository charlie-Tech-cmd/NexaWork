import { Icon } from "./Icon";
import { useState } from "react";
import { records, type RecordData } from "./api";
import { type Call } from "./Directory";
import { DataForm, Empty, ErrorState, PageHeading, Status } from "./ui";
import { useResource } from "./useResource";
function RoleDetails({ role, call }: { role: RecordData; call: Call }) {
  const resource = useResource(
    async (signal) =>
      records(
        await call(`/roles/${role.id}/permissions`, "GET", undefined, signal),
      ),
    [role.id],
  );
  return (
    <section className="panel">
      <div className="panel-toolbar">
        <div>
          <h2>{String(role.name)} permissions</h2>
          <p className="muted">Access granted by this role.</p>
        </div>
      </div>
      {resource.loading ? (
        <p role="status" className="loading">
          Loading permissions…
        </p>
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : resource.data?.length ? (
        <ul className="permission-list">
          {resource.data.map((permission) => (
            <li key={permission.id}>
              <strong>{String(permission.name)}</strong>
              <span className="muted">
                {String(permission.description || "")}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <Empty
          title="No permissions assigned"
          text="This role does not grant any permissions yet."
        />
      )}
    </section>
  );
}
export function Roles({ call }: { call: Call }) {
  const [editor, setEditor] = useState(false);
  const [selected, setSelected] = useState<RecordData | null>(null);
  const [notice, setNotice] = useState("");
  const resource = useResource(
    async (signal) => records(await call("/roles", "GET", undefined, signal)),
    [],
  );
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / ACCESS"
        title="The right access."
        description="Understand the roles that shape your organization."
      >
        <button className="primary" onClick={() => setEditor(true)}>
          + Create role
        </button>
      </PageHeading>
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {editor && (
        <section className="panel editor">
          <h2>Create a role</h2>
          <DataForm
            fields={[
              {
                name: "name",
                label: "Role name",
                minLength: 2,
                maxLength: 100,
              },
              { name: "description", label: "Description", optional: true },
            ]}
            submit="Create role"
            onCancel={() => setEditor(false)}
            onSave={async (data) => {
              await call("/roles", "POST", data);
              setEditor(false);
              setNotice(
                "Role created. It has no permissions until an administrator assigns them.",
              );
              resource.reload();
            }}
          />
        </section>
      )}
      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>Workspace roles</h2>
            <p className="muted">Select a role to inspect its permissions.</p>
          </div>
        </div>
        {resource.loading ? (
          <p role="status" className="loading">
            Loading roles…
          </p>
        ) : resource.error ? (
          <ErrorState message={resource.error} retry={resource.reload} />
        ) : resource.data?.length ? (
          <div className="role-list">
            {resource.data.map((role) => (
              <button
                className="role-row"
                key={role.id}
                onClick={() => setSelected(role)}
                aria-pressed={selected?.id === role.id}
              >
                <span className="structure-icon" aria-hidden="true">
                  <Icon name="shield" />
                </span>
                <span>
                  <strong>{String(role.name)}</strong>
                  <small>{String(role.description || "No description")}</small>
                </span>
                <Status active={role.is_active} />
                <Icon name="arrow" />
              </button>
            ))}
          </div>
        ) : (
          <Empty
            title="No roles yet"
            text="Create roles to organize workspace access."
          />
        )}
      </section>
      {selected && <RoleDetails role={selected} call={call} />}
    </>
  );
}
