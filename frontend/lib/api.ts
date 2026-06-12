const LOCAL_API = "http://localhost:8000";

/** Resolved at build time; empty string means "not configured" (not same-origin). */
export function getApiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  if (process.env.NODE_ENV === "development") {
    return LOCAL_API;
  }
  return "";
}

export function hasApiBackend(): boolean {
  return getApiBaseUrl().length > 0;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readResponseBody(res: Response): Promise<unknown> {
  const contentType = res.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return res.json();
  }

  const preview = (await res.text()).slice(0, 120).replace(/\s+/g, " ");
  const base = getApiBaseUrl();

  if (!base) {
    throw new ApiError(
      "No API backend is configured for this deployment. " +
        "Run setup.cmd locally for full evaluation, or set NEXT_PUBLIC_API_URL on Vercel " +
        "to your deployed FastAPI URL."
    );
  }

  if (preview.toLowerCase().includes("<!doctype") || preview.toLowerCase().includes("<html")) {
    throw new ApiError(
      `API at ${base} returned HTML instead of JSON. ` +
        "Is the FastAPI server running? Start it with setup.cmd or docker compose."
    );
  }

  throw new ApiError(
    `Unexpected response from API (${res.status}): ${preview || "empty body"}`
  );
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getApiBaseUrl();
  if (!base) {
    throw new ApiError("API backend is not configured.");
  }

  const res = await fetch(`${base}${path}`, init);
  const data = await readResponseBody(res);

  if (!res.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? (data as { detail?: unknown }).detail
        : data;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" &&
            detail !== null &&
            "message" in detail &&
            typeof (detail as { message: unknown }).message === "string"
          ? (detail as { message: string }).message
          : `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }

  return data as T;
}

export async function loadDemoEvaluation(): Promise<Record<string, unknown>> {
  const res = await fetch("/demo-evaluation.json");
  if (!res.ok) {
    throw new ApiError("Demo evaluation file is missing.");
  }
  return res.json() as Promise<Record<string, unknown>>;
}

export async function postEvaluate(
  form: FormData
): Promise<Record<string, unknown>> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/evaluate`, { method: "POST", body: form });
  const data = (await readResponseBody(res)) as Record<string, unknown>;

  if (res.status === 428) {
    throw new ApiError("GPU consent required", 428);
  }

  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" &&
            detail !== null &&
            "message" in detail &&
            typeof (detail as { message: unknown }).message === "string"
          ? (detail as { message: string }).message
          : "Evaluation failed";
    throw new ApiError(message, res.status);
  }

  return data;
}
