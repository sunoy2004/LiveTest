import type { GuardianConsentStatus, MentoringProfileMeResponse } from "@/types/domain";

/**
 * When the backend is not wired, local SPA behavior is driven by env (DPDP / minor flows).
 * @see Workflow Document — Onboarding & DPDP Compliance
 */
export function getDevGuardianConsentStatus(): GuardianConsentStatus {
  const v = import.meta.env.VITE_DEV_GUARDIAN_CONSENT as string | undefined;
  if (v === "PENDING" || v === "GRANTED" || v === "NOT_REQUIRED") return v;
  return "NOT_REQUIRED";
}

export function getDevIsMinor(): boolean {
  return import.meta.env.VITE_DEV_IS_MINOR === "true";
}

/** Offline / mock profile aligned with GET /api/v1/profiles/me */
export function getDevProfileFallback(): MentoringProfileMeResponse {
  return {
    mentee: {
      user_id: "00000000-0000-0000-0000-000000000001",
      learning_goals: ["Python", "System design"],
      education_level: "College",
      is_minor: getDevIsMinor(),
      guardian_consent_status: getDevGuardianConsentStatus(),
      cached_credit_score: 42,
    },
  };
}
