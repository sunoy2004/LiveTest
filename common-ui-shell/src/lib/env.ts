/**
 * Utilities for robust environment variable parsing in the shell.
 */

/**
 * Normalizes a base URL from environment variables.
 * Handles doubled URLs (e.g. "https://...https://...") caused by CI/CD shell interpolation issues.
 * Trims trailing slashes.
 */
export function normalizeBaseUrl(url: string | undefined, defaultValue: string): string {
  let raw = url?.trim();
  if (!raw) return defaultValue.replace(/\/$/, "");

  // Fix doubling: if the string contains "http" multiple times, take only the first one.
  const protocolIndex = raw.lastIndexOf("http");
  if (protocolIndex > 0) {
    console.warn(`[shell] Detected doubled URL in env. Recovering from: ${raw}`);
    raw = raw.substring(0, protocolIndex).trim();
  }

  return raw.replace(/\/$/, "");
}
