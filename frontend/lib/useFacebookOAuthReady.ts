"use client";

import { useEffect, useState } from "react";
import { fetchHealth, hasApiBackend } from "@/lib/api";
import { isBackendFacebookOAuthEnabled } from "@/lib/auth";

/** True when backend has FACEBOOK_APP_ID + FACEBOOK_APP_SECRET configured. */
export function useFacebookOAuthReady(): boolean | null {
  const [ready, setReady] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isBackendFacebookOAuthEnabled() || !hasApiBackend()) {
      setReady(false);
      return;
    }

    let cancelled = false;
    void fetchHealth()
      .then((health) => {
        if (!cancelled) setReady(Boolean(health.facebook_oauth));
      })
      .catch(() => {
        if (!cancelled) setReady(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return ready;
}
