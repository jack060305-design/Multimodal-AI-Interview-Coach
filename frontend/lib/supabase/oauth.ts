import { getSupabase, oauthRedirectUrl } from "@/lib/supabase/client";

export function isGoogleOAuthEnabled(): boolean {
  return process.env.NEXT_PUBLIC_OAUTH_GOOGLE_ENABLED === "true";
}

export function isFacebookOAuthEnabled(): boolean {
  return process.env.NEXT_PUBLIC_OAUTH_FACEBOOK_ENABLED === "true";
}

export function hasAnyOAuthEnabled(): boolean {
  return isGoogleOAuthEnabled() || isFacebookOAuthEnabled();
}

/** Map Supabase / OAuth API errors to user-friendly text. */
export function formatAuthError(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes("provider is not enabled") || lower.includes("unsupported provider")) {
    return (
      "Google/Facebook chưa bật trên Supabase. Vào Dashboard → Authentication → Providers → " +
      "bật Google (hoặc Facebook) và thêm Client ID/Secret."
    );
  }
  if (lower.includes("invalid login credentials")) {
    return "Email hoặc mật khẩu không đúng.";
  }
  if (lower.includes("user already registered")) {
    return "Email đã được đăng ký — hãy đăng nhập.";
  }
  if (lower.includes("email not confirmed")) {
    return "Vui lòng xác nhận email trước khi đăng nhập (kiểm tra hộp thư).";
  }
  return raw;
}

export async function signInWithOAuthProvider(
  provider: "google" | "facebook"
): Promise<string | null> {
  const sb = getSupabase();
  if (!sb) {
    return "Supabase chưa cấu hình — kiểm tra NEXT_PUBLIC_SUPABASE_URL và PUBLISHABLE_KEY.";
  }

  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: oauthRedirectUrl(),
      queryParams:
        provider === "google"
          ? { access_type: "offline", prompt: "consent" }
          : undefined,
    },
  });

  return error ? formatAuthError(error.message) : null;
}
