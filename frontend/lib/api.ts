const LOCAL_API = "http://localhost:8000";

import { authHeaders } from "./auth";

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: { id: string; email: string | null; name: string; avatar_url: string | null };
};

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

/** User-facing hint when OpenAI/Gemini quota or billing blocks AI features. */
export function friendlyApiErrorMessage(raw: string, status?: number): string {
  const lower = raw.toLowerCase();
  if (
    status === 429 ||
    lower.includes("insufficient_quota") ||
    lower.includes("exceeded your current quota") ||
    lower.includes("resource_exhausted")
  ) {
    return (
      "AI API quota exceeded. Add billing/credits on OpenAI (or Gemini), then redeploy. " +
      "Practice flow and question bank still work; video grading and daily agents need credits."
    );
  }
  if (lower.includes("openai_api_key") || lower.includes("api key")) {
    return "API key missing or invalid on the server. Check GitHub/Azure secrets and redeploy.";
  }
  if (
    status === 503 &&
    (lower.includes("database") || lower.includes("postgres") || lower.includes("db_"))
  ) {
    return (
      "Database not connected on the API server. " +
      "Set DATABASE_URL in GitHub Secrets (Supabase Postgres password) and redeploy Azure."
    );
  }
  return raw;
}

export type HealthStatus = {
  status: string;
  deploy_profile?: string;
  whisper_backend?: string;
  llm_provider?: string;
  langsmith?: boolean;
  db_enabled?: boolean;
  db_connected?: boolean;
  db_error?: string | null;
  auth_enabled?: boolean;
  facebook_oauth?: boolean;
};

export async function fetchHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>("/health");
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

  const headers = await authHeaders();
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...(init?.headers as Record<string, string> | undefined),
    },
  });
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
    throw new ApiError(friendlyApiErrorMessage(message, res.status), res.status);
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
  const headers = await authHeaders();
  const res = await fetch(`${base}/evaluate`, {
    method: "POST",
    headers,
    body: form,
  });
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
    throw new ApiError(friendlyApiErrorMessage(message, res.status), res.status);
  }

  return data;
}

export type PreviewQuestion = {
  question_id: string;
  question: string;
  competency?: string;
  source?: string;
};

export async function fetchRandomQuestion(
  role: string,
  difficulty = 3
): Promise<PreviewQuestion> {
  return fetchJson<PreviewQuestion>(
    `/interview/questions/${role}/random?difficulty=${difficulty}`
  );
}

export type QuestionFeedStatus = {
  synced_at: string | null;
  total: number;
  by_role: Record<string, number>;
  bank_counts: Record<string, number>;
  attribution?: string[];
};

export type DailyQuestionStatus = {
  generated_at: string | null;
  total: number;
  by_role: Record<string, number>;
  theme_today: string;
  enabled: boolean;
  cron_utc: string;
  per_role: number;
  mode: string;
  max_revisions: number;
  agents: string[];
  llm_calls_last_run?: number | null;
  agent_trace?: Array<{ node: string; decision: string }> | null;
  critic_notes?: string | null;
  bank_counts: Record<string, number>;
};

export async function fetchQuestionFeedStatus(): Promise<QuestionFeedStatus> {
  return fetchJson<QuestionFeedStatus>("/questions/feed/status");
}

export async function fetchDailyQuestionStatus(): Promise<DailyQuestionStatus> {
  return fetchJson<DailyQuestionStatus>("/questions/daily/status");
}

export async function postInterviewVideoTurn(
  sessionId: string,
  form: FormData
): Promise<Record<string, unknown>> {
  const base = getApiBaseUrl();
  const headers = await authHeaders();
  const res = await fetch(`${base}/interview/sessions/${sessionId}/turn/video`, {
    method: "POST",
    headers,
    body: form,
  });
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
          : "Video turn failed";
    throw new ApiError(friendlyApiErrorMessage(message, res.status), res.status);
  }

  return data;
}

export async function authRegister(body: {
  email: string;
  password: string;
  name: string;
}): Promise<AuthResponse> {
  return fetchJson<AuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function authLogin(body: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return fetchJson<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function syncUserProfile(): Promise<AuthResponse["user"]> {
  return fetchJson<AuthResponse["user"]>("/auth/me");
}

export async function fetchMyEvaluations(): Promise<
  Array<{
    evaluation_id: string;
    role: string;
    question: string;
    overall_score: number;
    created_at: string;
  }>
> {
  return fetchJson("/me/evaluations");
}
