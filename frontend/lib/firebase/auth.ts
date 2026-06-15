import {
  GoogleAuthProvider,
  type User,
  browserPopupRedirectResolver,
  getAuth,
  getRedirectResult,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut,
  type Auth,
} from "firebase/auth";

import type { AuthUser } from "@/lib/auth-types";
import { getFirebaseApp, isFirebaseConfigured, isFirebaseGoogleAuthEnabled } from "@/lib/firebase/config";

export function getFirebaseAuth(): Auth | null {
  const app = getFirebaseApp();
  if (!app) return null;
  return getAuth(app);
}

export function mapFirebaseUser(user: User): AuthUser {
  return {
    id: user.uid,
    email: user.email,
    name: user.displayName || user.email?.split("@")[0] || "User",
    avatar_url: user.photoURL,
    provider: "google",
  };
}

export async function getFirebaseIdToken(forceRefresh = false): Promise<string | null> {
  const auth = getFirebaseAuth();
  const user = auth?.currentUser;
  if (!user) return null;
  try {
    return await user.getIdToken(forceRefresh);
  } catch {
    return null;
  }
}

export function waitForFirebaseUser(maxMs = 4000): Promise<User | null> {
  const auth = getFirebaseAuth();
  if (!auth) return Promise.resolve(null);
  if (auth.currentUser) return Promise.resolve(auth.currentUser);

  return new Promise((resolve) => {
    const deadline = Date.now() + maxMs;
    const unsub = onAuthStateChanged(auth, (user) => {
      if (user) {
        unsub();
        resolve(user);
      } else if (Date.now() >= deadline) {
        unsub();
        resolve(null);
      }
    });
    setTimeout(() => {
      unsub();
      resolve(auth.currentUser);
    }, maxMs);
  });
}

/** Google sign-in via Firebase popup — branded picker on your Firebase/auth domain. */
function firebaseErrorCode(err: unknown): string {
  return err && typeof err === "object" && "code" in err
    ? String((err as { code?: string }).code)
    : "";
}

function formatFirebaseAuthError(err: unknown): string {
  const code = firebaseErrorCode(err);
  const message = err instanceof Error ? err.message : "Google sign-in failed";

  if (code === "auth/configuration-not-found") {
    return (
      "Firebase Authentication chưa được bật. Vào Firebase Console → Build → Authentication → " +
      "Get started → Sign-in method → bật Google → Save."
    );
  }
  if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") {
    return "Google sign-in was cancelled.";
  }
  if (code === "auth/popup-blocked") {
    return "Popup blocked by browser — allow popups for localhost or try again.";
  }
  if (code === "auth/operation-not-allowed") {
    return (
      "Google sign-in is not enabled in Firebase. " +
      "Open Authentication → Sign-in method → Google → Enable."
    );
  }
  if (code === "auth/unauthorized-domain") {
    return (
      "This site is not authorized in Firebase. " +
      "Add localhost (and 127.0.0.1) under Authentication → Settings → Authorized domains."
    );
  }
  if (code === "auth/invalid-api-key" || message.toLowerCase().includes("api key")) {
    return "Invalid Firebase API key — copy apiKey again from Firebase Project settings → Your apps.";
  }
  if (message.toLowerCase().includes("requested action is invalid")) {
    return (
      "Firebase Google login is not ready. Enable Google under Authentication → Sign-in method, " +
      "add localhost to Authorized domains, and verify NEXT_PUBLIC_FIREBASE_API_KEY in .env.local."
    );
  }
  return code ? `${message} (${code})` : message;
}

/** Complete sign-in after signInWithRedirect (call on login page mount). */
export async function completeFirebaseRedirectSignIn(): Promise<"signed-in" | null> {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  try {
    const result = await getRedirectResult(auth);
    if (!result?.user) return null;
    return "signed-in";
  } catch (err) {
    // Auth not enabled in Firebase Console yet — ignore on page load
    if (firebaseErrorCode(err) === "auth/configuration-not-found") {
      return null;
    }
    throw new Error(formatFirebaseAuthError(err));
  }
}

export async function signInWithGoogleFirebase(): Promise<string | null> {
  const auth = getFirebaseAuth();
  if (!auth) {
    return (
      "Firebase chưa cấu hình — thêm NEXT_PUBLIC_FIREBASE_* vào .env.local " +
      "(xem scripts/setup-firebase-supabase.ps1)."
    );
  }

  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });

  try {
    await signInWithPopup(auth, provider, browserPopupRedirectResolver);
    return null;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "";
    const code = firebaseErrorCode(err);

    const useRedirect =
      code === "auth/popup-blocked" ||
      message.toLowerCase().includes("requested action is invalid");

    if (useRedirect) {
      try {
        await signInWithRedirect(auth, provider, browserPopupRedirectResolver);
        return null;
      } catch (redirectErr) {
        return formatFirebaseAuthError(redirectErr);
      }
    }

    return formatFirebaseAuthError(err);
  }
}

export async function signOutFirebase(): Promise<void> {
  const auth = getFirebaseAuth();
  if (auth?.currentUser) {
    await signOut(auth);
  }
}

export function subscribeFirebaseAuth(
  onChange: (user: User | null) => void
): (() => void) | null {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  return onAuthStateChanged(auth, onChange);
}

export { isFirebaseConfigured, isFirebaseGoogleAuthEnabled };
