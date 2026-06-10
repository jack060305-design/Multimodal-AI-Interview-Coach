const STORAGE_KEY = "interview_coach_gpu_consent";

export type GpuConsent = "once" | "always" | "never";

export function getStoredGpuConsent(): GpuConsent | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "once" || v === "always" || v === "never") return v;
  return null;
}

export function setStoredGpuConsent(choice: GpuConsent): void {
  if (choice === "once") return;
  localStorage.setItem(STORAGE_KEY, choice);
}

export function clearStoredGpuConsent(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export type GpuStatusLite = {
  requires_prompt?: boolean;
  resolved_consent?: string;
  stored_consent?: string | null;
};

export function resolveConsentForRequest(
  gpuStatus: GpuStatusLite | null,
  pendingOnce: GpuConsent | null
): GpuConsent | null {
  if (pendingOnce === "once") return "once";
  if (gpuStatus?.resolved_consent === "always") return "always";
  if (gpuStatus?.resolved_consent === "never") return "never";
  const stored = getStoredGpuConsent();
  if (stored === "always" || stored === "never") return stored;
  if (gpuStatus?.requires_prompt) return null;
  return stored;
}
