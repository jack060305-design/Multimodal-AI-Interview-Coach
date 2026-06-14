"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { completeAuthFlow, setAuthSession } from "@/lib/auth";
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

    const finish = async () => {
      const authError = params.get("error_description") || params.get("error");
      if (authError) {
        setError(formatAuthError(decodeURIComponent(authError)));
        return;
      }

      const code = params.get("code");
      if (code) {
        const { error: err } = await sb.auth.exchangeCodeForSession(code);
        if (err) {
          setError(formatAuthError(err.message));
          return;
        }
        await completeAuthFlow(router);
        return;
      }

      const { data, error: err } = await sb.auth.getSession();
      if (err) {
        setError(formatAuthError(err.message));
        return;
      }
      if (data.session) {
        await completeAuthFlow(router);
      } else {
        setError("No active session — please sign in again.");
      }
    };

    void finish();
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
