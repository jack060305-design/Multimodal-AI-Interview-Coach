"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { completeAuthFlow, setAuthSession } from "@/lib/auth";
import { getSupabase } from "@/lib/supabase/client";
import { formatAuthError } from "@/lib/supabase/oauth";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const legacyToken = params.get("token");
    if (legacyToken) {
      setAuthSession({
        access_token: legacyToken,
        user: { id: "", email: null, name: "User", avatar_url: null },
      });
      void completeAuthFlow(router);
      return;
    }

    const sb = getSupabase();
    if (!sb) {
      setError("Supabase is not configured.");
      return;
    }

    const authError = params.get("error_description") || params.get("error");
    if (authError) {
      setError(formatAuthError(decodeURIComponent(authError)));
      return;
    }

    let settled = false;
    const finish = async () => {
      if (settled) return;
      settled = true;
      try {
        await completeAuthFlow(router);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not complete sign-in");
      }
    };

    const { data: sub } = sb.auth.onAuthStateChange((event: AuthChangeEvent, session: Session | null) => {
      if (session && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
        void finish();
      }
    });

    void (async () => {
      const code = params.get("code");
      if (code) {
        const { error: err } = await sb.auth.exchangeCodeForSession(code);
        if (err) {
          setError(formatAuthError(err.message));
          return;
        }
        await finish();
        return;
      }

      const { data, error: err } = await sb.auth.getSession();
      if (err) {
        setError(formatAuthError(err.message));
        return;
      }
      if (data.session) {
        await finish();
      } else {
        setError("No active session — please sign in again.");
      }
    })();

    return () => sub.subscription.unsubscribe();
  }, [params, router]);

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-600">{error}</p>
        <Link href="/login" className="mt-4 inline-block font-medium text-coach-blue hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return <p className="text-center text-slate-600">Completing sign-in…</p>;
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <CallbackHandler />
    </Suspense>
  );
}
