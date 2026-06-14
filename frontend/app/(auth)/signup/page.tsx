"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import AuthOAuthIcons from "@/components/AuthOAuthIcons";
import { authRegister } from "@/lib/api";
import { completeAuthFlow, isSupabaseConfigured, setAuthSession } from "@/lib/auth";
import { getSupabase, oauthRedirectUrl } from "@/lib/supabase/client";
import { formatAuthError } from "@/lib/supabase/oauth";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const useSupabase = isSupabaseConfigured();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const sb = getSupabase();
      if (sb) {
        const { data, error: err } = await sb.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: name },
            emailRedirectTo: oauthRedirectUrl(),
          },
        });
        if (err) throw new Error(formatAuthError(err.message));

        if (data.session) {
          await completeAuthFlow(router);
          return;
        }

        setInfo(
          "Account created. Check your email to confirm, then sign in. " +
            "(Or disable Confirm email in Supabase → Authentication → Email.)"
        );
        return;
      }
      const data = await authRegister({ email, password, name });
      setAuthSession(data);
      await completeAuthFlow(router);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900">Create account</h2>
      <p className="mt-1 text-sm text-slate-600">
        Your profile is saved to the database when you start practicing.
      </p>

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
      {info && (
        <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{info}</p>
      )}

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700">Name</label>
          <input
            type="text"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist bg-white px-3 py-2.5 text-slate-900 outline-none ring-coach-blue/30 focus:ring-2"
          />
        </div>
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
          <label className="text-sm font-medium text-slate-700">Password (min 8 characters)</label>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
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
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-coach-blue hover:underline">
          Sign in
        </Link>
      </p>

      {useSupabase && <AuthOAuthIcons onError={setError} />}
    </>
  );
}
