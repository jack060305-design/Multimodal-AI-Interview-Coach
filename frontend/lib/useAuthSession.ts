"use client";

import { useEffect, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { subscribeFirebaseAuth } from "@/lib/firebase/auth";
import { isFirebaseGoogleAuthEnabled } from "@/lib/firebase/config";
import { getSupabase } from "@/lib/supabase/client";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

/** Session token for API calls — Supabase or Firebase depending on how user signed in. */
export function useAuthSession() {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const sync = async () => {
      const t = await getAccessToken();
      if (!cancelled) {
        setToken(t);
        setReady(true);
      }
    };

    void sync();

    const cleanups: Array<() => void> = [];

    const sb = getSupabase();
    if (sb) {
      const { data: sub } = sb.auth.onAuthStateChange(
        (_event: AuthChangeEvent, _session: Session | null) => {
          void sync();
        }
      );
      cleanups.push(() => sub.subscription.unsubscribe());
    }

    if (isFirebaseGoogleAuthEnabled()) {
      const unsub = subscribeFirebaseAuth(() => {
        void sync();
      });
      if (unsub) cleanups.push(unsub);
    }

    const onStorage = (e: StorageEvent) => {
      if (e.key === "ic_access_token" || e.key === "ic_user") void sync();
    };
    window.addEventListener("storage", onStorage);
    cleanups.push(() => window.removeEventListener("storage", onStorage));

    return () => {
      cancelled = true;
      cleanups.forEach((fn) => fn());
    };
  }, []);

  return { token, signedIn: Boolean(token), ready };
}
