import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

function getSupabaseKeys(): { url: string; key: string } | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) return null;
  return { url, key };
}

/** Browser-only Supabase client — stores PKCE verifier in cookies via @supabase/ssr. */
export function getSupabase(): SupabaseClient | null {
  if (typeof window === "undefined") return null;

  const keys = getSupabaseKeys();
  if (!keys) return null;

  if (!client) {
    client = createBrowserClient(keys.url, keys.key);
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
