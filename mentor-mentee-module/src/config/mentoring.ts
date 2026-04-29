/**
 * Aligns with Architecture Document: Mentoring microservice REST surface (API Gateway → Cloud Run FastAPI).
 * Workflow Document: AI recommendations bypass Mentoring API (separate base URL).
 */

export const MENTORING_API_VERSION = "v1" as const;
export const MENTORING_API_PREFIX = `/api/${MENTORING_API_VERSION}`;

const USER_SERVICE_PROXY_PATH = "/user-service";

/**
 * Same mistake as `VITE_USER_SERVICE_URL`: pointing at the shell/MFE port with no `/user-service` prefix
 * makes `/api/v1/search` hit the frontend host → 404.
 */
function isLikelyMisconfiguredLocalMentoringUrl(base: string): boolean {
  try {
    const u = new URL(base);
    if (!(u.hostname === "localhost" || u.hostname === "127.0.0.1")) return false;
    if (u.pathname.startsWith(USER_SERVICE_PROXY_PATH)) return false;
    const port = u.port || (u.protocol === "https:" ? "443" : "80");
    if (port === "8000") return false;
    const mfe = String(import.meta.env.VITE_MFE_REMOTE_PORT || "5001");
    const suspicious = new Set(["8080", "3000", "5001", "4173", "5173", "5176", mfe]);
    return suspicious.has(port);
  } catch {
    return false;
  }
}

function isBareSameOriginAsPage(normalized: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const u = new URL(normalized);
    const w = new URL(window.location.href);
    return u.origin === w.origin && (u.pathname === "" || u.pathname === "/");
  } catch {
    return false;
  }
}

function mentoringProxyBase(): string {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}${USER_SERVICE_PROXY_PATH}`.replace(/\/$/, "");
}

/** Mentoring FastAPI (expects API Gateway to inject X-User-Id). */
export function getMentoringApiBaseUrl(): string {
  // Production: use the User Service URL because scheduling, dashboard, and
  // session routes live on the User Service (not the Mentoring Service).
  // The nginx static server now has a /user-service/ proxy to handle this.
  const userServiceUrl = (import.meta.env.VITE_USER_SERVICE_URL as string | undefined)?.trim();
  if (userServiceUrl) {
    const normalized = userServiceUrl.replace(/\/$/, "");
    if (!isLikelyMisconfiguredLocalMentoringUrl(normalized) && !isBareSameOriginAsPage(normalized)) {
      return normalized;
    }
  }

  // Fallback: try VITE_MENTORING_API_BASE_URL (may point to Mentoring Service
  // which only has /requests, /profiles, /search — not scheduling/dashboard)
  const mentoringUrl = (import.meta.env.VITE_MENTORING_API_BASE_URL as string | undefined)?.trim();
  if (mentoringUrl) {
    const normalized = mentoringUrl.replace(/\/$/, "");
    if (!isLikelyMisconfiguredLocalMentoringUrl(normalized) && !isBareSameOriginAsPage(normalized)) {
      return normalized;
    }
  }

  // Local dev & Prod fallback: use same-origin proxy (Vite or Nginx proxies /user-service → Backend)
  return mentoringProxyBase();
}



/** AI Matching / Graph service — Workflow 2: GET /recommendations (not routed through Mentoring API). */
export function getAiApiBaseUrl(): string {
  return (import.meta.env.VITE_AI_API_BASE_URL ?? "").replace(/\/$/, "");
}

export function isMentoringApiConfigured(): boolean {
  return getMentoringApiBaseUrl().length > 0;
}

export function isAiApiConfigured(): boolean {
  return getAiApiBaseUrl().length > 0;
}

/** Architecture §3 — REST paths (all under /api/v1). */
export const mentoringPaths = {
  profilesMe: `${MENTORING_API_PREFIX}/profiles/me`,
  profilesMentee: `${MENTORING_API_PREFIX}/profiles/mentee`,
  search: `${MENTORING_API_PREFIX}/search`,
  schedulingAvailability: (mentorId: string) =>
    `${MENTORING_API_PREFIX}/scheduling/availability?mentor_id=${encodeURIComponent(mentorId)}`,
  schedulingBook: `${MENTORING_API_PREFIX}/scheduling/book`,
  dashboardUpcomingSession: `${MENTORING_API_PREFIX}/dashboard/upcoming-session`,
  dashboardGoals: `${MENTORING_API_PREFIX}/dashboard/goals`,
  dashboardVault: `${MENTORING_API_PREFIX}/dashboard/vault`,
  /** Workflow 2 — mentorship request pitch (Gateway); Architecture lists domain under relationship engine. */
  requests: `${MENTORING_API_PREFIX}/requests`,
  requestStatus: (requestId: string) =>
    `${MENTORING_API_PREFIX}/requests/${encodeURIComponent(requestId)}/status`,

  sessionHistory: (sessionId: string) =>
    `${MENTORING_API_PREFIX}/sessions/${encodeURIComponent(sessionId)}/history`,
  /** User Service admin surface (not under mentoring prefix); use with `VITE_USER_SERVICE_URL`. */
  adminTier: (tierId: string) => `/admin/tiers/${encodeURIComponent(tierId)}`,
  adminRevokeConsent: (menteeId: string) =>
    `/admin/profiles/${encodeURIComponent(menteeId)}/revoke-consent`,
  adminResolveDispute: (disputeId: string) =>
    `/admin/disputes/${encodeURIComponent(disputeId)}/resolve`,
} as const;

/** Workflow 2 — AI discovery endpoint (relative to VITE_AI_API_BASE_URL). */
export const aiPaths = {
  recommendations: "/recommendations",
  recommendationsFeedback: "/recommendations/feedback",
} as const;
