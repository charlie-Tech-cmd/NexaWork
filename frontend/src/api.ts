export type RecordData = { id: number; [key: string]: unknown };
export type Session = {
  token: string;
  name: string;
  email: string;
  id: number;
  mode: string;
};
export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}
export function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
export function record(value: unknown): RecordData {
  if (
    !value ||
    typeof value !== "object" ||
    !("id" in value) ||
    typeof value.id !== "number"
  ) {
    throw new ApiError(
      "The server returned an unexpected response. Please contact your administrator.",
    );
  }
  return value as RecordData;
}
export function records(value: unknown): RecordData[] {
  if (!Array.isArray(value))
    throw new ApiError("The server returned an unexpected list.");
  return value.map(record);
}
export function loginSession(value: unknown, mode: string): Session {
  const data = record(value);
  if (
    typeof data.access_token !== "string" ||
    !data.access_token ||
    typeof data.full_name !== "string" ||
    typeof data.email !== "string"
  ) {
    throw new ApiError("The server returned an incomplete sign-in response.");
  }
  return {
    token: data.access_token,
    name: data.full_name,
    email: data.email,
    id: data.id,
    mode,
  };
}
function detailMessage(data: unknown): string | undefined {
  if (!data || typeof data !== "object" || !("detail" in data)) return;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return "Invalid field";
        const field = Array.isArray(item.loc)
          ? item.loc.filter((part: unknown) => part !== "body").join(" · ")
          : "Field";
        return `${field}: ${typeof item.msg === "string" ? item.msg : "Invalid value"}`;
      })
      .join(". ");
}
export async function request(
  path: string,
  token = "",
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<unknown> {
  if (!path.startsWith("/") || path.startsWith("//"))
    throw new ApiError("Invalid request path.");
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(20000)])
        : AbortSignal.timeout(20000),
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      "Could not reach your workspace. Check your connection and try again.",
    );
  }
  if (response.status === 204) return null;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback =
      response.status === 403
        ? "You do not have access to this action. Ask your administrator for permission."
        : response.status === 401
          ? "Your session has expired. Please sign in again."
          : response.status === 429
            ? "Too many requests. Please wait before trying again."
            : "Your workspace could not complete this request. Please try again.";
    throw new ApiError(
      response.status >= 500 ? fallback : detailMessage(data) || fallback,
      response.status,
    );
  }
  if (data === null)
    throw new ApiError("The server returned an unreadable response.");
  return data;
}
export function structurePath(level: number, parentId: number): string {
  const paths = [
    "regions/organizations",
    "branches/regions",
    "departments/branches",
    "teams/departments",
  ];
  if (!paths[level] || !Number.isInteger(parentId) || parentId < 1)
    throw new ApiError("Select a parent workspace first.");
  return `/${paths[level]}/${parentId}`;
}
export function structurePayload(
  level: number,
  parentId: number,
  data: object,
): object {
  return level === 3 ? { ...data, department_id: parentId } : data;
}
