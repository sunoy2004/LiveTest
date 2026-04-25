/**
 * Utilities for robust environment variable parsing in the Mentee UI.
 */

export function normalizeBaseUrl(url: string | undefined, defaultValue: string): string {
  let raw = url?.trim();
  if (!raw) return defaultValue.replace(/\/$/, "");

  const protocolIndex = raw.lastIndexOf("http");
  if (protocolIndex > 0) {
    console.warn(`[mentee-ui] Detected doubled URL in env. Recovering from: ${raw}`);
    raw = raw.substring(0, protocolIndex).trim();
  }

  return raw.replace(/\/$/, "");
}
