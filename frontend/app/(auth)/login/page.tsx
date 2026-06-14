"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import AuthOAuthIcons from "@/components/AuthOAuthIcons";
import { authLogin } from "@/lib/api";
import { completeAuthFlow, isSupabaseConfigured, setAuthSession } from "@/lib/auth";
import { getSupabase } from "@/lib/supabase/client";
import { formatAuthError } from "@/lib/supabase/oauth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    params.get("error_description") || params.get("error")
      ? formatAuthError(
          decodeURIComponent(params.get("error_description") || params.get("error") || "")
        )
      : null
  );
  const [loading, setLoading] = useState(false);
  const useSupabase = isSupabaseConfigured();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const sb = getSupabase();
      if (sb) {
        const { error: err } = await sb.auth.signInWithPassword({ email, password });
        if (err) throw new Error(formatAuthError(err.message));
        await completeAuthFlow(router);
        return;
      }
      const data = await authLogin({ email, password });
      setAuthSession(data);
      await completeAuthFlow(router);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900">Sign in</h2>
      <p className="mt-1 text-sm text-slate-600">
        Use your email and password to access the interview coach.
      </p>

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700">Email</label>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist bg-white px-3 py-2.5 text-slate-900 outline-none ring-coach-blue/30 focus:ring-2"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700">Password</label>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist bg-white px-3 py-2.5 text-slate-900 outline-none ring-coach-blue/30 focus:ring-2"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="auth-btn-primary w-full rounded-lg bg-coach-blue py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-coach-cyan disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        No account?{" "}
        <Link href="/signup" className="font-semibold text-coach-blue hover:underline">
          Create account
        </Link>
      </p>

      {useSupabase && <AuthOAuthIcons onError={setError} />}
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
