"use client";

import { useState } from "react";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import { signInWithOAuthProvider } from "@/lib/supabase/oauth";

function GoogleIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path
        fill="#1877F2"
        d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"
      />
    </svg>
  );
}

type Props = {
  onError?: (message: string) => void;
};

export default function AuthOAuthIcons({ onError }: Props) {
  const [loading, setLoading] = useState<"google" | "facebook" | null>(null);

  if (!isSupabaseConfigured()) return null;

  const startOAuth = async (provider: "google" | "facebook") => {
    setLoading(provider);
    const msg = await signInWithOAuthProvider(provider);
    if (msg) onError?.(msg);
    setLoading(null);
  };

  return (
    <div className="mt-4">
      <p className="text-center text-xs text-slate-500">Or continue with</p>
      <div className="mt-3 flex items-center justify-center gap-3">
        <button
          type="button"
          title="Sign in with Google"
          aria-label="Sign in with Google"
          disabled={loading !== null}
          onClick={() => void startOAuth("google")}
          className="auth-oauth-btn flex h-11 w-11 items-center justify-center rounded-full border border-coach-mist bg-white shadow-sm transition hover:border-coach-blue/40 hover:shadow-md disabled:opacity-50"
        >
          {loading === "google" ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-coach-blue border-t-transparent" />
          ) : (
            <GoogleIcon />
          )}
        </button>
        <button
          type="button"
          title="Sign in with Facebook"
          aria-label="Sign in with Facebook"
          disabled={loading !== null}
          onClick={() => void startOAuth("facebook")}
          className="auth-oauth-btn flex h-11 w-11 items-center justify-center rounded-full border border-coach-mist bg-white shadow-sm transition hover:border-coach-blue/40 hover:shadow-md disabled:opacity-50"
        >
          {loading === "facebook" ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-coach-blue border-t-transparent" />
          ) : (
            <FacebookIcon />
          )}
        </button>
      </div>
    </div>
  );
}
