"use client";

import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase/client";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

/** Wait for Supabase session cookies to load before calling protected APIs. */
export function useAuthSession() {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const sb = getSupabase();
    if (!sb) {
      setReady(true);
      return;
    }

    const sync = async () => {
      const { data } = await sb.auth.getSession();
      setToken(data.session?.access_token ?? null);
      setReady(true);
    };

    void sync();

    const { data: sub } = sb.auth.onAuthStateChange(
      (_event: AuthChangeEvent, session: Session | null) => {
        setToken(session?.access_token ?? null);
        setReady(true);
      }
    );

    return () => sub.subscription.unsubscribe();
  }, []);

  return { token, signedIn: Boolean(token), ready };
}
