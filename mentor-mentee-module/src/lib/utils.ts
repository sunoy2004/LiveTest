import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Case-insensitive match across displayed fields (admin directory tables). */
export function matchesAdminSearch(query: string, ...parts: (string | number | null | undefined)[]): boolean {
  const s = query.trim().toLowerCase();
  if (!s) return true;
  return parts.some((p) => String(p ?? "").toLowerCase().includes(s));
}
