import { useState } from "react";
import {
  records,
  structurePath,
  structurePayload,
  type RecordData,
} from "./api";
import { type Call } from "./Directory";
import { DataForm, Empty, ErrorState, PageHeading, Status } from "./ui";
import { useResource } from "./useResource";
const levels = ["Regions", "Branches", "Departments", "Teams"];
const singular = ["region", "branch", "department", "team"];
export function Structure({
  call,
  organization,
}: {
  call: Call;
  organization: RecordData;
}) {
  const [trail, setTrail] = useState<RecordData[]>([]);
  const [editor, setEditor] = useState(false);
  const [notice, setNotice] = useState("");
  const level = trail.length;
  const parent = trail.at(-1) || organization;
  const path = structurePath(level, parent.id);
  const resource = useResource(
    async (signal) => records(await call(path, "GET", undefined, signal)),
    [path],
  );
  function navigate(next: RecordData[]) {
    setTrail(next);
    setEditor(false);
    setNotice("");
  }
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / ORGANIZATION"
        title="A place for every team."
        description="Explore how your people and places connect."
      >
        <button className="primary" onClick={() => setEditor(true)}>
          + Add {singular[level]}
        </button>
      </PageHeading>
      <nav className="breadcrumbs" aria-label="Organization hierarchy">
        <button onClick={() => navigate([])}>
          {String(organization.name)}
        </button>
        {trail.map((item, index) => (
          <span key={`${index}-${item.id}`}>
            {" "}
            /{" "}
            <button onClick={() => navigate(trail.slice(0, index + 1))}>
              {String(item.name)}
            </button>
          </span>
        ))}
      </nav>
      <div className="hierarchy-steps">
        {levels.map((name, index) => (
          <div key={name} className={index === level ? "current" : ""}>
            <span>0{index + 1}</span>
            {name}
            <small>
              {index === level
                ? "You are here"
                : index < level
                  ? "Selected"
                  : "Explore next"}
            </small>
          </div>
        ))}
      </div>
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {editor && (
        <section className="panel editor">
          <h2>Add {singular[level]}</h2>
          <p className="muted">Within {String(parent.name)}</p>
          <DataForm
            fields={[
              { name: "name", label: "Name", minLength: 2 },
              { name: "slug", label: "Handle", minLength: 2, maxLength: 100 },
            ]}
            submit={`Create ${singular[level]}`}
            onCancel={() => setEditor(false)}
            onSave={async (data) => {
              await call(
                path,
                "POST",
                structurePayload(level, parent.id, data),
              );
              setEditor(false);
              setNotice(`${levels[level].slice(0, -1)} created.`);
              resource.reload();
            }}
          />
        </section>
      )}
      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>{levels[level]}</h2>
            <p className="muted">
              {String(parent.name)}{" "}
              {resource.data
                ? `· ${resource.data.length} ${levels[level].toLowerCase()}`
                : ""}
            </p>
          </div>
          <button
            className="secondary"
            onClick={resource.reload}
            disabled={resource.loading}
          >
            Refresh
          </button>
        </div>
        {resource.loading ? (
          <p className="loading" role="status">
            Loading {levels[level].toLowerCase()}…
          </p>
        ) : resource.error ? (
          <ErrorState message={resource.error} retry={resource.reload} />
        ) : resource.data?.length ? (
          <div className="structure-grid">
            {resource.data.map((item) => (
              <article className="structure-card" key={item.id}>
                <div className="card-top">
                  <span className="structure-icon" aria-hidden="true">
                    {["◎", "⌂", "▦", "◇"][level]}
                  </span>
                  <Status active={item.is_active} />
                </div>
                <h3>{String(item.name)}</h3>
                <p className="muted">{String(item.slug)}</p>
                {level < 3 ? (
                  <button
                    className="text-button"
                    onClick={() => navigate([...trail, item])}
                  >
                    View {levels[level + 1].toLowerCase()} →
                  </button>
                ) : (
                  <span className="muted">Team #{item.id}</span>
                )}
              </article>
            ))}
          </div>
        ) : (
          <Empty
            title={`Your ${levels[level].toLowerCase()} start here`}
            text={`Add a ${singular[level]} within ${String(parent.name)} to organize your workspace.`}
          />
        )}
      </section>
    </>
  );
}
