"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { setAuthSession, type AuthResponse, type AuthUser } from "@/lib/auth";

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("Missing token from Facebook login");
      return;
    }

    (async () => {
      try {
        const user = await fetchJson<AuthUser>("/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const session: AuthResponse = {
          access_token: token,
          token_type: "bearer",
          user,
        };
        setAuthSession(session);
        router.replace("/practice");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not complete login");
      }
    })();
  }, [params, router]);

  if (error) {
    return (
      <div className="px-6 py-16 text-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-16 text-center text-slate-600">Completing sign-in…</div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <CallbackHandler />
    </Suspense>
  );
}
