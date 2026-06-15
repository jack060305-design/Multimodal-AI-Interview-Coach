import { getSupabase } from "@/lib/supabase/client";
import { formatAuthError } from "@/lib/supabase/oauth";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: { type?: string; shape?: string; size?: string; theme?: string }
          ) => void;
        };
      };
    };
  }
}

/** Same Web Client ID as Google Cloud Console (not the Supabase redirect flow). */
export function getGoogleWebClientId(): string | null {
  return process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() || null;
}

export function useBrandedGoogleSignIn(): boolean {
  return getGoogleWebClientId() !== null;
}

let gsiScriptPromise: Promise<void> | null = null;

function loadGsiScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gsiScriptPromise) return gsiScriptPromise;

  gsiScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Google sign-in script"));
    document.head.appendChild(script);
  });
  return gsiScriptPromise;
}

/** Sign in via Google ID token — picker shows your app domain, not *.supabase.co */
export async function signInWithGoogleIdToken(credential: string): Promise<string | null> {
  const sb = getSupabase();
  if (!sb) {
    return "Supabase chưa cấu hình — kiểm tra NEXT_PUBLIC_SUPABASE_URL và PUBLISHABLE_KEY.";
  }

  const { error } = await sb.auth.signInWithIdToken({
    provider: "google",
    token: credential,
  });

  return error ? formatAuthError(error.message) : null;
}

/** Open Google account picker from our custom icon button (no broken iframe). */
export async function runGoogleIdTokenSignIn(): Promise<string | null> {
  const clientId = getGoogleWebClientId();
  if (!clientId) {
    return "NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured.";
  }

  try {
    await loadGsiScript();
  } catch {
    return "Could not load Google sign-in. Check your network connection.";
  }

  if (!window.google?.accounts?.id) {
    return "Google sign-in is not available in this browser.";
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (msg: string | null) => {
      if (settled) return;
      settled = true;
      host.remove();
      resolve(msg);
    };

    const host = document.createElement("div");
    host.style.position = "fixed";
    host.style.left = "-9999px";
    host.style.top = "0";
    document.body.appendChild(host);

    window.google!.accounts.id.initialize({
      client_id: clientId,
      auto_select: false,
      callback: (response) => {
        void signInWithGoogleIdToken(response.credential).then(finish);
      },
    });

    window.google!.accounts.id.renderButton(host, {
      type: "standard",
      theme: "outline",
      size: "large",
    });

    const clickTarget =
      host.querySelector<HTMLElement>('[role="button"]') ??
      host.querySelector<HTMLElement>("div");

    if (!clickTarget) {
      finish("Google sign-in button could not be rendered.");
      return;
    }

    clickTarget.click();

    window.setTimeout(() => {
      finish("Google sign-in was cancelled or blocked.");
    }, 120_000);
  });
}
