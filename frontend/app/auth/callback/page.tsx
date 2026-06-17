"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { completeAuthFlow, formatFacebookAuthError, setAuthSession } from "@/lib/auth";
import { getSupabase } from "@/lib/supabase/client";
import { formatAuthError } from "@/lib/supabase/oauth";

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const legacyToken = params.get("token");
    if (legacyToken) {
      setAuthSession({
        access_token: legacyToken,
        user: { id: "", email: null, name: "User", avatar_url: null, provider: "facebook" },
      });
      void completeAuthFlow(router).catch((err) => {
        setError(err instanceof Error ? err.message : "Could not complete sign-in");
      });
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

    let cancelled = false;

    void (async () => {
      const code = params.get("code");
      if (code) {
        const { error: err } = await sb.auth.exchangeCodeForSession(code);
        if (cancelled) return;
        if (err) {
          setError(formatAuthError(err.message));
          return;
        }
        try {
          await completeAuthFlow(router);
        } catch (err) {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : "Could not complete sign-in");
          }
        }
        return;
      }

      const { data, error: err } = await sb.auth.getSession();
      if (cancelled) return;
      if (err) {
        setError(formatAuthError(err.message));
        return;
      }
      if (data.session) {
        try {
          await completeAuthFlow(router);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Could not complete sign-in");
        }
      } else {
        setError("No active session — please sign in again.");
      }
    })();

    return () => {
      cancelled = true;
    };
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
