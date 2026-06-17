import { ApiError, syncUserProfile } from "@/lib/api";
import type { AuthUser } from "@/lib/auth-types";
import {
  getFirebaseAuth,
  getFirebaseIdToken,
  isFirebaseConfigured,
  isFirebaseGoogleAuthEnabled,
  mapFirebaseUser,
  signOutFirebase,
  waitForFirebaseUser,
} from "@/lib/firebase/auth";
import { getSupabase, isSupabaseConfigured } from "@/lib/supabase/client";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

export type { AuthUser } from "@/lib/auth-types";

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

export async function waitForAccessToken(maxMs = 4000): Promise<string | null> {
  if (isFirebaseGoogleAuthEnabled()) {
    const user = await waitForFirebaseUser(maxMs);
    if (user) {
      const token = await getFirebaseIdToken();
      if (token) return token;
    }
  }

  const sb = getSupabase();
  if (!sb) {
    return getStoredToken();
  }

  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    const { data } = await sb.auth.getSession();
    if (data.session?.access_token) {
      return data.session.access_token;
    }
    const legacy = getStoredToken();
    if (legacy) return legacy;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return getStoredToken();
}

export async function getAccessToken(): Promise<string | null> {
  if (isFirebaseGoogleAuthEnabled()) {
    const firebaseToken = await getFirebaseIdToken();
    if (firebaseToken) return firebaseToken;
  }

  const sb = getSupabase();
  if (sb) {
    const { data } = await sb.auth.getSession();
    if (data.session?.access_token) return data.session.access_token;
  }
  return getStoredToken();
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  if (isFirebaseConfigured()) {
    const user = getFirebaseAuth()?.currentUser;
    if (user) return mapFirebaseUser(user);
  }

  const sb = getSupabase();
  if (sb) {
    const { data } = await sb.auth.getUser();
    const u = data.user;
    if (u) {
      const meta = u.user_metadata || {};
      return {
        id: u.id,
        email: u.email ?? null,
        name: meta.full_name || meta.name || u.email?.split("@")[0] || "User",
        avatar_url: meta.avatar_url || meta.picture || null,
        provider: u.app_metadata?.provider,
      };
    }
  }
  return getStoredUser();
}

function clearLegacySession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function signOutAuth(): Promise<void> {
  await signOutFirebase();
  clearLegacySession();
  const sb = getSupabase();
  if (sb) {
    await sb.auth.signOut();
  }
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

/** Backend Graph API OAuth (redirect to FastAPI /auth/facebook/login). */
export function isBackendFacebookOAuthEnabled(): boolean {
  return process.env.NEXT_PUBLIC_BACKEND_FACEBOOK_OAUTH === "true";
}

export function formatFacebookAuthError(raw: string): string {
  const code = raw.trim().toLowerCase();
  if (code === "invalid_oauth_state") {
    return "Phiên Facebook đã hết hạn — hãy thử đăng nhập lại.";
  }
  if (code === "facebook_profile_missing") {
    return "Không lấy được thông tin Facebook — kiểm tra quyền email/public_profile trên Meta App.";
  }
  if (code === "facebook_not_configured") {
    return (
      "Facebook login chưa cấu hình trên API. Chạy scripts/setup-facebook-backend-oauth.ps1 " +
      "với FACEBOOK_APP_ID và FACEBOOK_APP_SECRET, rồi restart setup.cmd."
    );
  }
  if (code === "account_disabled") {
    return "Tài khoản đã bị vô hiệu hóa — liên hệ quản trị viên.";
  }
  if (code.includes("facebook login not configured") || code.includes("not configured")) {
    return "Facebook login chưa cấu hình — thêm FACEBOOK_APP_ID và FACEBOOK_APP_SECRET vào backend/.env.";
  }
  if (code.includes("access denied") || code.includes("user denied")) {
    return "Bạn đã hủy đăng nhập Facebook.";
  }
  return raw;
}

export { isSupabaseConfigured, isFirebaseConfigured, isFirebaseGoogleAuthEnabled };

function formatDatabaseSyncError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) {
      const api = process.env.NEXT_PUBLIC_API_URL || "";
      const isLocal = api.includes("localhost") || api.includes("127.0.0.1");
      const detail = err.message?.trim();
      if (isLocal) {
        return (
          "API database not connected. Restart the backend after setting DB_ENABLED=true in backend/.env " +
          "(local uses SQLite automatically). Check http://127.0.0.1:8000/health for db_connected."
        );
      }
      if (detail && detail.toLowerCase().includes("sync failed")) {
        return `Signed in, but profile sync failed on the API: ${detail}`;
      }
      if (detail && !detail.startsWith("Database not connected")) {
        return `Signed in, but the API returned an error: ${detail}`;
      }
      return (
        "Signed in, but the API database is not connected. " +
        "Set DATABASE_URL in GitHub Secrets and redeploy Azure."
      );
    }
    if (err.status === 401) {
      const api = process.env.NEXT_PUBLIC_API_URL || "";
      const isLocal = api.includes("localhost") || api.includes("127.0.0.1");
      if (isLocal) {
        if (isFirebaseGoogleAuthEnabled()) {
          return (
            "API could not verify your Firebase/Google session. Set FIREBASE_PROJECT_ID in backend/.env " +
            "to match NEXT_PUBLIC_FIREBASE_PROJECT_ID, then restart setup.cmd."
          );
        }
        const legacy = getStoredUser();
        if (legacy?.provider === "facebook") {
          return "Phiên Facebook không hợp lệ — đăng xuất và đăng nhập lại bằng Facebook.";
        }
        return (
          "API could not verify your Google session. Restart setup.cmd so backend/.env has " +
          "SUPABASE_URL and SUPABASE_ANON_KEY, then sign in again."
        );
      }
      return "Session could not be verified by the API. Sign out and sign in again.";
    }
    return err.message;
  }
  return err instanceof Error ? err.message : "Could not sync profile to database";
}

/** Persist auth user into backend Postgres (users table). */
export async function syncUserToDatabase(): Promise<AuthUser | null> {
  const token = await waitForAccessToken();
  if (!token) {
    throw new Error("Session not ready — please try signing in again.");
  }
  return syncUserProfile();
}

/** After login/signup: save to DB then open the app. */
export async function completeAuthFlow(router: AppRouterInstance): Promise<void> {
  if (hasApiBackend()) {
    try {
      const profile = await syncUserToDatabase();
      const legacyToken = getStoredToken();
      const sb = getSupabase();
      const { data: sbSession } = sb ? await sb.auth.getSession() : { data: { session: null } };
      if (profile && legacyToken && !sbSession?.session) {
        setAuthSession({
          access_token: legacyToken,
          user: {
            id: profile.id,
            email: profile.email,
            name: profile.name,
            avatar_url: profile.avatar_url,
            provider: "facebook",
          },
        });
      }
    } catch (err) {
      throw new Error(formatDatabaseSyncError(err));
    }
  }
  router.replace("/practice");
}

function hasApiBackend(): boolean {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return true;
  return process.env.NODE_ENV === "development";
}
