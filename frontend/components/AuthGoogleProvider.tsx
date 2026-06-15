"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { getGoogleWebClientId } from "@/lib/supabase/google-id-token";

export default function AuthGoogleProvider({ children }: { children: React.ReactNode }) {
  const clientId = getGoogleWebClientId();
  if (!clientId) return <>{children}</>;
  return <GoogleOAuthProvider clientId={clientId}>{children}</GoogleOAuthProvider>;
}
