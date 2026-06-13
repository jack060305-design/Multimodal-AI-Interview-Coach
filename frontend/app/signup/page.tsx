"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { authRegister } from "@/lib/api";
import { facebookLoginUrl, setAuthSession } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await authRegister({ email, password, name });
      setAuthSession(data);
      router.push("/practice");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-semibold text-slate-900">Create account</h1>
      <p className="mt-2 text-sm text-slate-600">Email sign-up or Facebook — your evaluations are saved to Postgres.</p>

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist px-3 py-2"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist px-3 py-2"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700">Password (min 8)</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-coach-mist px-3 py-2"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-coach-blue py-2.5 text-sm font-medium text-white hover:bg-coach-blue/90 disabled:opacity-60"
        >
          {loading ? "Creating…" : "Sign up with email"}
        </button>
      </form>

      <a
        href={facebookLoginUrl()}
        className="mt-3 flex w-full items-center justify-center rounded-lg border border-coach-mist bg-white py-2.5 text-sm font-medium text-slate-800 hover:bg-slate-50"
      >
        Sign up with Facebook
      </a>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-coach-blue hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
