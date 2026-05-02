import { MentoringApiError } from "@/lib/api/client";

/** Safe description for toast — never returns "[object Object]". */
export function formatApiError(e: unknown): string {
  if (e instanceof MentoringApiError && typeof e.message === "string" && e.message.trim()) {
    return e.message.trim().slice(0, 500);
  }
  if (e instanceof Error && typeof e.message === "string" && e.message.trim()) {
    const m = e.message.trim();
    if (m !== "[object Object]") return m.slice(0, 500);
  }
  if (e && typeof e === "object") {
    const o = e as Record<string, unknown>;
    if (typeof o.message === "string" && o.message.trim()) return o.message.trim().slice(0, 500);
    if (typeof o.detail === "string" && o.detail.trim()) return o.detail.trim().slice(0, 500);
    try {
      return JSON.stringify(e).slice(0, 500);
    } catch {
      return "Request failed";
    }
  }
  return "Request failed";
}
