import { type FirebaseApp, getApp, getApps, initializeApp } from "firebase/app";

export type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
};

export function getFirebaseConfig(): FirebaseWebConfig | null {
  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY?.trim();
  const authDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN?.trim();
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID?.trim();
  const appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID?.trim();
  if (!apiKey || !authDomain || !projectId || !appId) return null;
  return { apiKey, authDomain, projectId, appId };
}

/** Firebase handles Google sign-in; Supabase handles email + Postgres. */
export function isFirebaseConfigured(): boolean {
  return getFirebaseConfig() !== null;
}

/** Use Firebase Google popup only after enabling Auth in Firebase Console. */
export function isFirebaseGoogleAuthEnabled(): boolean {
  return (
    isFirebaseConfigured() &&
    process.env.NEXT_PUBLIC_FIREBASE_AUTH_ENABLED?.trim().toLowerCase() === "true"
  );
}

export function getFirebaseApp(): FirebaseApp | null {
  const config = getFirebaseConfig();
  if (!config) return null;
  if (getApps().length) return getApp();
  return initializeApp(config);
}
