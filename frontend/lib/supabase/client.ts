import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

import { getFirebaseIdToken } from "@/lib/firebase/auth";
import { isFirebaseGoogleAuthEnabled } from "@/lib/firebase/config";

let client: SupabaseClient | null = null;
let clientUsesFirebaseToken = false;

function getSupabaseKeys(): { url: string; key: string } | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) return null;
  return { url, key };
}

/** Browser-only Supabase client — PKCE cookies; Firebase JWT only when Firebase Google auth is on. */
export function getSupabase(): SupabaseClient | null {
  if (typeof window === "undefined") return null;

  const keys = getSupabaseKeys();
  if (!keys) return null;

  const firebaseTokenMode = isFirebaseGoogleAuthEnabled();
  if (!client || clientUsesFirebaseToken !== firebaseTokenMode) {
    clientUsesFirebaseToken = firebaseTokenMode;
    const options = firebaseTokenMode
      ? {
          accessToken: async () => (await getFirebaseIdToken()) ?? null,
        }
      : undefined;
    client = createBrowserClient(keys.url, keys.key, options);
  }
  return client;
}

export function isSupabaseConfigured(): boolean {
  return getSupabaseKeys() !== null;
}

export function oauthRedirectUrl(): string {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/auth/callback`;
  }
  return (
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
    "http://localhost:3000"
  ) + "/auth/callback";
}
