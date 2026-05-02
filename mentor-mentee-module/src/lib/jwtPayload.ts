/** Decode `role` from a User Service JWT (same issuer as mentoring). No signature verify — UI hint only. */

export function rolesFromAccessToken(token: string | null | undefined): string[] {
  if (!token?.includes(".")) return [];
  try {
    const b64 = token.split(".")[1];
    const json = atob(b64.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as { role?: unknown };
    const raw = payload.role;
    if (Array.isArray(raw)) return raw.map((r) => String(r));
    if (raw != null && raw !== "") return [String(raw)];
  } catch {
    /* ignore */
  }
  return [];
}

/** Same JWT as `rolesFromAccessToken` — used when `/me` is unavailable (e.g. network). */
export function isAdminFromAccessToken(token: string | null | undefined): boolean {
  if (!token?.includes(".")) return false;
  try {
    const b64 = token.split(".")[1];
    const json = atob(b64.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as { role?: unknown; is_admin?: boolean };
    if (payload.is_admin === true) return true;
    return rolesFromAccessToken(token).includes("ADMIN");
  } catch {
    return false;
  }
}
