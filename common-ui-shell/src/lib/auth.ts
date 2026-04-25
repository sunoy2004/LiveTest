import { normalizeBaseUrl } from "./env";
export const AUTH_TOKEN_KEY = "cui.auth_token";
export const AUTH_USER_KEY = "cui.auth_user";

export type AuthUser = {
  id: string;
  email: string;
  is_admin?: boolean;
};

export function readStoredAuth(): { token: string | null; user: AuthUser | null } {
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const raw = localStorage.getItem(AUTH_USER_KEY);
    if (!token || !raw) return { token: null, user: null };
    const user = JSON.parse(raw) as AuthUser;
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
}

export function persistAuth(token: string, user: AuthUser): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

const USER_SERVICE_PROXY_PATH = "/user-service";
// Prefer IPv4 for Firefox/Windows: `localhost` may resolve to `::1` while Uvicorn is bound to 127.0.0.1.
const DEFAULT_USER_SERVICE_DIRECT = "http://127.0.0.1:8000";

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
  const raw = import.meta.env.VITE_USER_SERVICE_URL as string | undefined;
  const normalized = normalizeBaseUrl(raw, DEFAULT_USER_SERVICE_DIRECT);

  if (raw) {
    if (isLikelyMisconfiguredLocalUserServiceUrl(normalized)) {
      console.warn(
        `[shell] VITE_USER_SERVICE_URL (${normalized}) looks like a frontend dev port, not User Service. ` +
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
