import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "@/lib/authStorage";
import { getAiApiBaseUrl, getMentoringApiBaseUrl } from "@/config/mentoring";


function readShellAuthHeaders(): { token: string | null; userId: string | null } {
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const raw = localStorage.getItem(AUTH_USER_KEY);
    if (!token || !raw) return { token: null, userId: null };
    const u = JSON.parse(raw) as { id?: string };
    return { token, userId: u.id ?? null };
  } catch {
    return { token: null, userId: null };
  }
}

export class MentoringApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "MentoringApiError";
  }
}

function mentoringHeaders(extra?: HeadersInit): Headers {
  const h = new Headers(extra);
  if (!h.has("Content-Type")) {
    h.set("Content-Type", "application/json");
  }
  const { token } = readShellAuthHeaders();
  if (token && !h.has("Authorization")) {
    h.set("Authorization", `Bearer ${token}`);
  }
  return h;
}

/**
 * Relative path must start with `/api/v1/...` (see mentoringPaths).
 * Sends Bearer + X-User-Id from the same keys as common-ui-shell when present.
 */
export async function mentoringFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const base = getMentoringApiBaseUrl();
  if (!base && !path.startsWith("http")) {
    throw new MentoringApiError("VITE_MENTORING_API_BASE_URL is not set", 0);
  }
  
  // If the path is already a full URL (starts with http), use it as is.
  // Otherwise, prepend the base.
  const url = path.startsWith("http") 
    ? path 
    : `${base}${path.startsWith("/") ? path : `/${path}`}`;
    
  const headers = mentoringHeaders(init?.headers);
  return fetch(url, { ...init, headers });
}

export async function mentoringJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await mentoringFetch(path, init);
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : undefined;
  } catch {
    parsed = text;
  }
  if (!res.ok) {
    throw new MentoringApiError(
      typeof parsed === "object" && parsed && "detail" in (parsed as object)
        ? String((parsed as { detail?: string }).detail)
        : res.statusText || "Request failed",
      res.status,
      parsed,
    );
  }
  return parsed as T;
}

/** Workflow 2 — direct call to AI Matching service (separate host from Mentoring API). */
export async function aiFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = getAiApiBaseUrl();
  if (!base && !path.startsWith("http")) {
    throw new MentoringApiError("VITE_AI_API_BASE_URL is not set", 0);
  }
  
  const url = path.startsWith("http") 
    ? path 
    : `${base}${path.startsWith("/") ? path : `/${path}`}`;
    
  const h = new Headers(init?.headers);
  if (!h.has("Content-Type") && init?.body) {
    h.set("Content-Type", "application/json");
  }
  const { token } = readShellAuthHeaders();
  if (token && !h.has("Authorization")) {
    h.set("Authorization", `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers: h });
}

export async function aiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await aiFetch(path, init);
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : undefined;
  } catch {
    parsed = text;
  }
  if (!res.ok) {
    throw new MentoringApiError(res.statusText || "AI request failed", res.status, parsed);
  }
  return parsed as T;
}
