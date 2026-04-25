import type { FullProfileResponse } from "@/types/userServiceProfile";

/** Vite dev/preview proxies this path to User Service — see `vite.config.ts`. */
export const USER_SERVICE_PROXY_PATH = "/user-service";

// Prefer IPv4 for Firefox/Windows: `localhost` may resolve to `::1` while Uvicorn is bound to 127.0.0.1.
const DEFAULT_USER_SERVICE_DIRECT = "http://127.0.0.1:8000";

/**
 * True when `VITE_USER_SERVICE_URL` points at a local dev/preview port instead of User Service (8000).
 * Common mistake: setting the URL to the MFE or shell port (e.g. 8080).
 */
function isLikelyMisconfiguredLocalUserServiceUrl(base: string): boolean {
  try {
    const u = new URL(base);
    if (u.pathname !== "/" && u.pathname !== "") return false;
    if (!(u.hostname === "localhost" || u.hostname === "127.0.0.1")) return false;
    const port = u.port || (u.protocol === "https:" ? "443" : "80");
    if (port === "8000") return false;
    const mfe = String(import.meta.env.VITE_MFE_REMOTE_PORT || "5001");
    const suspicious = new Set(["8080", "3000", "5001", "4173", "5173", mfe]);
    return suspicious.has(port);
  } catch {
    return false;
  }
}

function sameOriginProxyBase(): string {
  if (typeof window === "undefined") return DEFAULT_USER_SERVICE_DIRECT;
  return `${window.location.origin}${USER_SERVICE_PROXY_PATH}`.replace(/\/$/, "");
}

/** Same app origin with path `/` only — use proxy prefix so we never hit the shell (e.g. /ws) by mistake. */
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

export function getUserServiceBase(): string {
  const raw = (import.meta.env.VITE_USER_SERVICE_URL as string | undefined)?.trim();
  if (raw) {
    const normalized = raw.replace(/\/$/, "");
    if (isLikelyMisconfiguredLocalUserServiceUrl(normalized)) {
      console.warn(
        `[mentor] VITE_USER_SERVICE_URL (${normalized}) looks like a frontend dev port, not User Service. ` +
          `Using ${USER_SERVICE_PROXY_PATH} on this origin (see Vite proxy) or set to ${DEFAULT_USER_SERVICE_DIRECT}.`,
      );
      return sameOriginProxyBase();
    }
    if (isBareSameOriginAsPage(normalized)) {
      return sameOriginProxyBase();
    }
    return normalized;
  }
  if (typeof window !== "undefined") {
    return sameOriginProxyBase();
  }
  return DEFAULT_USER_SERVICE_DIRECT;
}

/** WebSocket URL for `/ws/dashboard?token=…` (User Service). */
export function getUserServiceDashboardWsUrl(token: string): string {
  const base = getUserServiceBase();
  const u = new URL(`${base}/ws/dashboard`);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.searchParams.set("token", token);
  return u.toString();
}

export async function fetchProfileFull(token: string): Promise<FullProfileResponse> {
  const res = await fetch(`${getUserServiceBase()}/profile/full`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Profile fetch failed (${res.status})`);
  }
  return res.json() as Promise<FullProfileResponse>;
}
