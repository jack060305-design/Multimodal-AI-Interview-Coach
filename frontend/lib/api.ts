import { MOCK_QUESTIONS, MOCK_ROLES, Question, Role } from "./mockData";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FETCH_TIMEOUT_MS = 5000;

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function loadRoles(): Promise<{ roles: Role[]; offline: boolean }> {
  try {
    const data = await fetchJson<{ roles?: Role[] }>(`${API_URL}/roles`);
    const roles = data.roles?.length ? data.roles : MOCK_ROLES;
    return { roles, offline: false };
  } catch {
    return { roles: MOCK_ROLES, offline: true };
  }
}

export async function loadQuestions(
  role: string
): Promise<{ questions: Question[]; offline: boolean }> {
  try {
    const data = await fetchJson<{ questions?: Question[] }>(`${API_URL}/questions/${role}`);
    const questions = data.questions?.length ? data.questions : MOCK_QUESTIONS[role] || [];
    return { questions, offline: false };
  } catch {
    return { questions: MOCK_QUESTIONS[role] || [], offline: true };
  }
}

export async function loadGpuStatus(): Promise<Record<string, unknown> | null> {
  try {
    return await fetchJson(`${API_URL}/gpu/status`);
  } catch {
    return null;
  }
}
