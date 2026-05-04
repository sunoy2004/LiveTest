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

/** Mentoring FastAPI (Authority for domain logic). */
export function getMentoringApiBaseUrl(): string {
  return getMentoringDomainBaseUrl();
}

/** 
 * Mentorship Domain Authority (Profiles, Connections, Requests).
 * Directs traffic to the Mentoring Service to ensure data consistency in mentoring.

 */
export function getMentoringDomainBaseUrl(): string {
  const mentoringUrl = (import.meta.env.VITE_MENTORING_API_BASE_URL as string | undefined)?.trim();
  if (mentoringUrl) {
    const normalized = mentoringUrl.replace(/\/$/, "");
    if (!isLikelyMisconfiguredLocalMentoringUrl(normalized) && !isBareSameOriginAsPage(normalized)) {
      return normalized;
    }
  }
  
  // Fallback to the same-origin proxy /mentoring-service (which we added to Nginx)
  if (typeof window === "undefined") return "";
  return `${window.location.origin}/mentoring-service`.replace(/\/$/, "");
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
  profilesMe: `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/profiles/me`,
  profilesMentee: `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/profiles/mentee`,
  profilesMentor: (mentorUserId: string) =>
    `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/profiles/mentor/${encodeURIComponent(mentorUserId)}`,
  search: `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/search`,
  schedulingAvailability: (mentorId: string) =>
    `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/scheduling/availability?mentor_id=${encodeURIComponent(mentorId)}`,
  schedulingBook: `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/scheduling/book`,
  dashboardUpcomingSession: `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/dashboard/upcoming-session`,
  dashboardGoals: `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/dashboard/goals`,
  dashboardVault: `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/dashboard/vault`,
  /** Workflow 2 — mentorship request pitch (Mentoring Service authority). */
  requests: `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/requests`,
  requestsHistory: (limit = 100) =>
    `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/requests/history?limit=${encodeURIComponent(String(limit))}`,
  requestStatus: (requestId: string) =>
    `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/requests/${encodeURIComponent(requestId)}/status`,
  sessionHistory: (sessionId: string) =>
    `${getMentoringDomainBaseUrl()}${MENTORING_API_PREFIX}/sessions/${encodeURIComponent(sessionId)}/history`,
  /** Relative path fragments under `${MENTORING_API_PREFIX}/admin` (use with `getMentoringDomainBaseUrl()`). */
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
