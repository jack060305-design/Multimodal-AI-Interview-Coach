import { getSupabase, isSupabaseConfigured } from "@/lib/supabase/client";
import { syncUserProfile } from "@/lib/api";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

export type AuthUser = {
  id: string;
  email: string | null;
  name: string;
  avatar_url: string | null;
  provider?: string;
};

const TOKEN_KEY = "ic_access_token";
const USER_KEY = "ic_user";

/** Legacy localStorage session (when Supabase is not configured). */
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export async function getAccessToken(): Promise<string | null> {
  const sb = getSupabase();
  if (sb) {
    const { data } = await sb.auth.getSession();
    return data.session?.access_token ?? null;
  }
  return getStoredToken();
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const sb = getSupabase();
  if (sb) {
    const { data } = await sb.auth.getUser();
    const u = data.user;
    if (!u) return null;
    const meta = u.user_metadata || {};
    return {
      id: u.id,
      email: u.email ?? null,
      name: meta.full_name || meta.name || u.email?.split("@")[0] || "User",
      avatar_url: meta.avatar_url || meta.picture || null,
      provider: u.app_metadata?.provider,
    };
  }
  return getStoredUser();
}

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function signOutAuth(): Promise<void> {
  const sb = getSupabase();
  if (sb) {
    await sb.auth.signOut();
    return;
  }
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** @deprecated legacy API login — use Supabase when configured */
export function setAuthSession(data: {
  access_token: string;
  user: AuthUser;
}): void {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function facebookLoginUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base.replace(/\/$/, "")}/auth/facebook/login`;
}

export { isSupabaseConfigured };

/** Persist Supabase user into backend Postgres (users table). */
export async function syncUserToDatabase(): Promise<void> {
  const token = await getAccessToken();
  if (!token) return;
  try {
    await syncUserProfile();
  } catch {
    // Backend DB may not be configured yet — Supabase auth still works locally.
  }
}

/** After login/signup: save to DB then open the app. */
export async function completeAuthFlow(router: AppRouterInstance): Promise<void> {
  await syncUserToDatabase();
  router.replace("/practice");
}
