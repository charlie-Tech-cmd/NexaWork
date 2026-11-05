import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  errorMessage,
  record,
  records,
  request,
  type RecordData,
} from "./api";
import { InvitationLink, type Call } from "./Directory";
import { Icon } from "./Icon";
import { DataForm, Empty, ErrorState, PageHeading, type Field } from "./ui";
import { useResource } from "./useResource";
import { Wordmark } from "./Wordmark";

type PublicMode = "register" | "accept" | "verify";
type RegistrationBranch = {
  id: number;
  name: string;
  departments: { id: number; name: string }[];
};

function objectValue(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object")
    throw new ApiError("The server returned an unexpected response.");
  return value as Record<string, unknown>;
}

function OnboardingField({
  label,
  name,
  type = "text",
  value,
  onChange,
  required = true,
  minLength,
}: {
  label: string;
  name: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  minLength?: number;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <label className="onboarding-field" htmlFor={name}>
      {label}
      {type === "password" ? (
        <span className="password-input-wrap">
          <input
            id={name}
            name={name}
            type={visible ? "text" : "password"}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            required={required}
            minLength={minLength}
            autoComplete="new-password"
          />
          <button
            type="button"
            className="password-toggle"
            aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`}
            aria-pressed={visible}
            onClick={() => setVisible((current) => !current)}
          >
            <Icon name={visible ? "eye-off" : "eye"} />
          </button>
        </span>
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          minLength={minLength}
          autoComplete={type === "email" ? "email" : "off"}
        />
      )}
    </label>
  );
}

export function PublicOnboarding({
  mode,
  token = "",
}: {
  mode: PublicMode;
  token?: string;
}) {
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [complete, setComplete] = useState(false);
  const [registrationCode, setRegistrationCode] = useState("");
  const [branches, setBranches] = useState<RegistrationBranch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [password, setPassword] = useState("");
  const [acceptancePassword, setAcceptancePassword] = useState("");
  const verificationRequest = useRef<Promise<unknown> | null>(null);

  useEffect(() => {
    if (mode !== "verify") return;
    let active = true;
    if (!token) {
      setError("This verification link is missing its token.");
      return;
    }
    verificationRequest.current ??= request(
      "/onboarding/verify-email",
      "",
      "POST",
      { token },
    );
    verificationRequest.current
      .then(() => {
        if (active) {
          setComplete(true);
          setNotice(
            "Your email is verified. Your request is ready for review.",
          );
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(errorMessage(cause));
      });
    return () => {
      active = false;
    };
  }, [mode, token]);

  async function loadOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = objectValue(
        await request("/onboarding/registration-structure", "", "POST", {
          registration_code: registrationCode.trim(),
        }),
      );
      const branchRows = records(response.branches).map((branch) => ({
        id: branch.id,
        name: String(branch.name),
        departments: records(branch.departments).map((department) => ({
          id: department.id,
          name: String(department.name),
        })),
      }));
      setBranches(branchRows);
      setBranchId("");
      setDepartmentId("");
      setNotice("");
      if (branchRows.length === 0)
        setError("This organization has no active branches available yet.");
    } catch (cause) {
      setError(errorMessage(cause));
      setBranches([]);
    } finally {
      setBusy(false);
    }
  }

  async function acceptInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("This invitation link is missing its token.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = record(
        await request("/onboarding/invitations/accept", "", "POST", {
          token,
          password: acceptancePassword,
        }),
      );
      if (typeof response.employee_id !== "string")
        throw new ApiError("The server did not return your employee ID.");
      setComplete(true);
      setNotice(
        `Your account is ready. Your Employee ID is ${response.employee_id}. Sign in using Employee ID and the password you chose.`,
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  async function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/onboarding/register", "", "POST", {
        full_name: fullName,
        email,
        password,
        job_title: jobTitle,
        branch_id: Number(branchId),
        department_id: Number(departmentId),
        registration_code: registrationCode.trim(),
      });
      setComplete(true);
      setNotice(
        "Check your email for a verification link to finish registration.",
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    setBusy(true);
    setError("");
    try {
      const response = objectValue(
        await request("/onboarding/resend-verification", "", "POST", {
          registration_code: registrationCode.trim(),
          email,
        }),
      );
      setNotice(String(response.message));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  const selectedBranch = branches.find(
    (branch) => String(branch.id) === branchId,
  );
  const title =
    mode === "register"
      ? "Join your organization."
      : mode === "accept"
        ? "Accept your invitation."
        : "Verify your email.";

  return (
    <main className="onboarding-page">
      <div className="onboarding-card">
        <Wordmark />
        <p className="eyebrow">EMPLOYEE ONBOARDING</p>
        <h1>{title}</h1>
        <p className="muted">
          {mode === "register"
            ? "Use the registration code shared by your organization."
            : mode === "accept"
              ? "Choose a password to activate your invited account."
              : "Confirming your email helps your administrator review your request."}
        </p>
        {notice && (
          <p className="notice success" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        {!complete && mode === "register" && branches.length === 0 && (
          <form className="data-form" onSubmit={loadOrganization}>
            <fieldset disabled={busy}>
              <OnboardingField
                label="Organization registration code"
                name="registration-code"
                value={registrationCode}
                onChange={setRegistrationCode}
                minLength={6}
              />
              <button className="primary" type="submit">
                {busy ? "Checking…" : "Continue"}
              </button>
            </fieldset>
          </form>
        )}
        {!complete && mode === "register" && branches.length > 0 && (
          <form className="data-form" onSubmit={submitRegistration}>
            <fieldset disabled={busy}>
              <OnboardingField
                label="Full name"
                name="full-name"
                value={fullName}
                onChange={setFullName}
                minLength={2}
              />
              <OnboardingField
                label="Work email"
                name="work-email"
                type="email"
                value={email}
                onChange={setEmail}
              />
              <OnboardingField
                label="Job title"
                name="job-title"
                value={jobTitle}
                onChange={setJobTitle}
                minLength={2}
              />
              <label className="onboarding-field" htmlFor="branch-id">
                Branch
                <select
                  id="branch-id"
                  value={branchId}
                  onChange={(event) => {
                    setBranchId(event.target.value);
                    setDepartmentId("");
                  }}
                  required
                >
                  <option value="">Choose a branch</option>
                  {branches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="onboarding-field" htmlFor="department-id">
                Department
                <select
                  id="department-id"
                  value={departmentId}
                  onChange={(event) => setDepartmentId(event.target.value)}
                  required
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
              <OnboardingField
                label="Password (8 characters minimum)"
                name="registration-password"
                type="password"
                value={password}
                onChange={setPassword}
                minLength={8}
              />
              <div className="form-actions">
                <button className="primary" type="submit">
                  {busy ? "Sending…" : "Request to join"}
                </button>
                <button
                  className="secondary"
                  type="button"
                  onClick={() => {
                    setBranches([]);
                    setNotice("");
                  }}
                >
                  Change code
                </button>
              </div>
            </fieldset>
          </form>
        )}
        {!complete && mode === "accept" && (
          <form className="data-form" onSubmit={acceptInvitation}>
            <fieldset disabled={busy}>
              <OnboardingField
                label="Create a password (8 characters minimum)"
                name="invitation-password"
                type="password"
                value={acceptancePassword}
                onChange={setAcceptancePassword}
                minLength={8}
              />
              <button className="primary" type="submit">
                {busy ? "Activating…" : "Accept invitation"}
              </button>
            </fieldset>
          </form>
        )}
        {!complete && mode === "verify" && (
          <p className="loading" role="status">
            Verifying your email…
          </p>
        )}
        {complete && mode === "register" && (
          <button
            className="secondary onboarding-resend"
            type="button"
            onClick={resendVerification}
            disabled={busy}
          >
            {busy ? "Sending…" : "Resend verification link"}
          </button>
        )}
        <p className="onboarding-signin">
          Already have an account? <a href="/sign-in">Sign in</a>
        </p>
      </div>
    </main>
  );
}

function runLoad(call: Call, path: string, signal: AbortSignal) {
  return call(path, "GET", undefined, signal).then(records);
}

function formatDate(value: unknown): string {
  if (typeof value !== "string") return "No expiry";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "No expiry" : date.toLocaleString();
}

export function OnboardingAdmin({ call }: { call: Call }) {
  const codes = useResource(
    (signal) => runLoad(call, "/onboarding/registration-codes", signal),
    [call],
  );
  const requests = useResource(
    (signal) => runLoad(call, "/onboarding/requests", signal),
    [call],
  );
  const invitations = useResource(
    (signal) => runLoad(call, "/onboarding/invitations", signal),
    [call],
  );
  const employees = useResource(
    (signal) => runLoad(call, "/onboarding/employees", signal),
    [call],
  );
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [lastInvitation, setLastInvitation] = useState<RecordData | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [newCode, setNewCode] = useState("");
  const [requestSearch, setRequestSearch] = useState("");
  const [requestStatus, setRequestStatus] = useState("all");
  const [invitationSearch, setInvitationSearch] = useState("");
  const [invitationStatus, setInvitationStatus] = useState("all");
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [employeeStatus, setEmployeeStatus] = useState("all");
  const inviteFields: Field[] = [
    { name: "full_name", label: "Full name", minLength: 2 },
    { name: "email", label: "Work email", type: "email" },
    { name: "job_title", label: "Job title", minLength: 2 },
    { name: "branch_id", label: "Branch ID", type: "number" },
    { name: "department_id", label: "Department ID", type: "number" },
  ];
  const visibleRequests = (requests.data || []).filter((item) => {
    const matchesStatus =
      requestStatus === "all" || item.approval_status === requestStatus;
    const haystack =
      `${item.full_name} ${item.email} ${item.job_title}`.toLowerCase();
    return matchesStatus && haystack.includes(requestSearch.toLowerCase());
  });
  const visibleInvitations = (invitations.data || []).filter((item) => {
    const matchesStatus =
      invitationStatus === "all" || item.status === invitationStatus;
    const haystack = `${item.full_name} ${item.email}`.toLowerCase();
    return matchesStatus && haystack.includes(invitationSearch.toLowerCase());
  });
  const visibleEmployees = (employees.data || []).filter((item) => {
    const matchesStatus =
      employeeStatus === "all" || item.account_status === employeeStatus;
    const haystack =
      `${item.full_name} ${item.email} ${item.job_title}`.toLowerCase();
    return matchesStatus && haystack.includes(employeeSearch.toLowerCase());
  });

  async function perform(action: () => Promise<unknown>, success: string) {
    setError("");
    setNotice("");
    setNewCode("");
    try {
      await action();
      setNotice(success);
      codes.reload();
      requests.reload();
      invitations.reload();
      employees.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function createCode() {
    setError("");
    setNotice("");
    setNewCode("");
    try {
      const result = record(
        await call("/onboarding/registration-codes", "POST", {
          expires_in_minutes: 1440,
        }),
      );
      setNewCode(String(result.code));
      setNotice(
        "Registration code created. Copy it now; it is not shown again.",
      );
      codes.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / ONBOARDING"
        title="Welcome people in."
        description="Manage registration codes, review requests, and keep employee access current."
      >
        <button
          className="primary"
          onClick={() => setShowInviteForm(!showInviteForm)}
        >
          {showInviteForm ? "Close invite form" : "+ Invite employee"}
        </button>
      </PageHeading>
      {notice && (
        <p className="notice success" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {newCode && (
        <section
          className="panel onboarding-code-reveal"
          aria-label="New registration code"
        >
          <strong>Copy this code now</strong>
          <code>{newCode}</code>
          <span className="muted">
            It expires in 24 hours and will not be shown again.
          </span>
        </section>
      )}
      {showInviteForm && (
        <section className="panel editor">
          <h2>Invite an employee</h2>
          <p className="muted">
            Create an invitation for an employee to choose their own password.
            Email delivery is simulated in this development setup; you can
            securely share the acceptance link.
          </p>
          <DataForm
            fields={inviteFields}
            submit="Send invitation"
            onCancel={() => setShowInviteForm(false)}
            onSave={async (data) => {
              const invitation = record(
                await call("/onboarding/invitations", "POST", {
                  ...data,
                  branch_id: Number(data.branch_id),
                  department_id: Number(data.department_id),
                }),
              );
              if (typeof invitation.acceptance_url !== "string")
                throw new Error(
                  "The server did not return an invitation link.",
                );
              setLastInvitation(invitation);
              setShowInviteForm(false);
              setNotice("Invitation created.");
              invitations.reload();
            }}
          />
        </section>
      )}
      {lastInvitation && <InvitationLink invitation={lastInvitation} />}

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>Registration codes</h2>
            <p className="muted">
              Active codes allow employees to request access. Each new code is
              shown only once.
            </p>
          </div>
          <button className="secondary" onClick={createCode}>
            + Create 24-hour code
          </button>
        </div>
        {codes.loading ? (
          <p className="loading" role="status">
            Loading registration codes…
          </p>
        ) : codes.error ? (
          <ErrorState message={codes.error} retry={codes.reload} />
        ) : codes.data?.length ? (
          <div className="onboarding-list">
            {codes.data.map((code) => (
              <div className="onboarding-row" key={code.id}>
                <div>
                  <strong>Code #{code.id}</strong>
                  <p className="muted">
                    {code.is_active ? "Active" : "Inactive"} · expires{" "}
                    {formatDate(code.expires_at)}
                  </p>
                </div>
                {code.is_active === true && (
                  <div className="onboarding-actions">
                    <button
                      className="secondary"
                      onClick={() =>
                        perform(async () => {
                          const replacement = record(
                            await call(
                              `/onboarding/registration-codes/${code.id}/rotate`,
                              "POST",
                              { expires_in_minutes: 1440 },
                            ),
                          );
                          setNewCode(String(replacement.code));
                        }, "Registration code rotated.")
                      }
                    >
                      Rotate
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        perform(
                          () =>
                            call(
                              `/onboarding/registration-codes/${code.id}/revoke`,
                              "POST",
                            ),
                          "Registration code revoked.",
                        )
                      }
                    >
                      Revoke
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No registration codes"
            text="Create a code to let employees request access to this workspace."
          />
        )}
      </section>

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>Employee registration requests</h2>
            <p className="muted">
              Only verified email addresses can be approved.
            </p>
          </div>
          <div className="onboarding-filters">
            <label>
              <span className="sr-only">Search registration requests</span>
              <input
                type="search"
                value={requestSearch}
                onChange={(event) => setRequestSearch(event.target.value)}
                placeholder="Search requests…"
              />
            </label>
            <label>
              <span className="sr-only">Filter registration requests</span>
              <select
                value={requestStatus}
                onChange={(event) => setRequestStatus(event.target.value)}
              >
                <option value="all">All requests</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>
          </div>
        </div>
        {requests.loading ? (
          <p className="loading" role="status">
            Loading requests…
          </p>
        ) : requests.error ? (
          <ErrorState message={requests.error} retry={requests.reload} />
        ) : visibleRequests.length ? (
          <div className="onboarding-list">
            {visibleRequests.map((item) => (
              <div className="onboarding-row" key={item.id}>
                <div>
                  <strong>{String(item.full_name)}</strong>
                  <p className="muted">
                    {typeof item.employee_id === "string" &&
                      `Employee ID ${item.employee_id} · `}
                    {String(item.email)} · {String(item.job_title)} · email{" "}
                    {String(item.email_verification_status)} · request{" "}
                    {String(item.approval_status)}
                  </p>
                </div>
                {item.approval_status === "pending" && (
                  <div className="onboarding-actions">
                    <button
                      className="secondary"
                      disabled={item.email_verification_status !== "verified"}
                      onClick={() =>
                        perform(
                          () =>
                            call(
                              `/onboarding/requests/${item.id}/approve`,
                              "POST",
                              {},
                            ),
                          "Registration approved.",
                        )
                      }
                    >
                      Approve
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        perform(
                          () =>
                            call(
                              `/onboarding/requests/${item.id}/reject`,
                              "POST",
                              { reason: "Rejected by administrator" },
                            ),
                          "Registration rejected.",
                        )
                      }
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : requests.data?.length ? (
          <Empty
            title="No matching requests"
            text="Change the search or status filter to see other requests."
          />
        ) : (
          <Empty
            title="No registration requests"
            text="New requests will appear here."
          />
        )}
      </section>

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>Invitations</h2>
            <p className="muted">Resend or revoke a pending invitation.</p>
          </div>
          <div className="onboarding-filters">
            <label>
              <span className="sr-only">Search invitations</span>
              <input
                type="search"
                value={invitationSearch}
                onChange={(event) => setInvitationSearch(event.target.value)}
                placeholder="Search invitations…"
              />
            </label>
            <label>
              <span className="sr-only">Filter invitations</span>
              <select
                value={invitationStatus}
                onChange={(event) => setInvitationStatus(event.target.value)}
              >
                <option value="all">All invitations</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="expired">Expired</option>
                <option value="revoked">Revoked</option>
              </select>
            </label>
          </div>
        </div>
        {invitations.loading ? (
          <p className="loading" role="status">
            Loading invitations…
          </p>
        ) : invitations.error ? (
          <ErrorState message={invitations.error} retry={invitations.reload} />
        ) : visibleInvitations.length ? (
          <div className="onboarding-list">
            {visibleInvitations.map((invitation) => (
              <div className="onboarding-row" key={invitation.id}>
                <div>
                  <strong>{String(invitation.full_name)}</strong>
                  <p className="muted">
                    {String(invitation.email)} · {String(invitation.status)} ·
                    expires {formatDate(invitation.expires_at)}
                  </p>
                </div>
                {invitation.status === "pending" && (
                  <div className="onboarding-actions">
                    <button
                      className="secondary"
                      onClick={() =>
                        perform(async () => {
                          const result = record(
                            await call(
                              `/onboarding/invitations/${invitation.id}/resend`,
                              "POST",
                            ),
                          );
                          if (typeof result.acceptance_url !== "string")
                            throw new Error(
                              "The server did not return an invitation link.",
                            );
                          setLastInvitation(result);
                          return result;
                        }, "Invitation renewed.")
                      }
                    >
                      Resend
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        perform(
                          () =>
                            call(
                              `/onboarding/invitations/${invitation.id}/revoke`,
                              "POST",
                            ),
                          "Invitation revoked.",
                        )
                      }
                    >
                      Revoke
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : invitations.data?.length ? (
          <Empty
            title="No matching invitations"
            text="Change the search or status filter to see other invitations."
          />
        ) : (
          <Empty
            title="No invitations"
            text="Invitations you create will appear here."
          />
        )}
      </section>

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>Employee accounts</h2>
            <p className="muted">
              Disable access or re-enable an employee account.
            </p>
          </div>
          <div className="onboarding-filters">
            <label>
              <span className="sr-only">Search employee accounts</span>
              <input
                type="search"
                value={employeeSearch}
                onChange={(event) => setEmployeeSearch(event.target.value)}
                placeholder="Search employees…"
              />
            </label>
            <label>
              <span className="sr-only">Filter employee accounts</span>
              <select
                value={employeeStatus}
                onChange={(event) => setEmployeeStatus(event.target.value)}
              >
                <option value="all">All accounts</option>
                <option value="active">Active</option>
                <option value="disabled">Disabled</option>
              </select>
            </label>
          </div>
        </div>
        {employees.loading ? (
          <p className="loading" role="status">
            Loading employee accounts…
          </p>
        ) : employees.error ? (
          <ErrorState message={employees.error} retry={employees.reload} />
        ) : visibleEmployees.length ? (
          <div className="onboarding-list">
            {visibleEmployees.map((employee) => (
              <div className="onboarding-row" key={employee.id}>
                <div>
                  <strong>{String(employee.full_name)}</strong>
                  <p className="muted">
                    Employee ID {String(employee.employee_id)} ·{" "}
                    {String(employee.email)} · {String(employee.job_title)} ·{" "}
                    {String(employee.account_status)}
                  </p>
                </div>
                <button
                  className="secondary"
                  onClick={() =>
                    perform(
                      () =>
                        call(
                          `/onboarding/employees/${employee.id}/${employee.account_status === "active" ? "disable" : "enable"}`,
                          "POST",
                          employee.account_status === "active"
                            ? { reason: "Disabled by administrator" }
                            : undefined,
                        ),
                      employee.account_status === "active"
                        ? "Employee account disabled."
                        : "Employee account enabled.",
                    )
                  }
                >
                  {employee.account_status === "active" ? "Disable" : "Enable"}
                </button>
              </div>
            ))}
          </div>
        ) : employees.data?.length ? (
          <Empty
            title="No matching employees"
            text="Change the search or status filter to see other employees."
          />
        ) : (
          <Empty
            title="No employee accounts"
            text="Approved employees will appear here."
          />
        )}
      </section>
    </>
  );
}
