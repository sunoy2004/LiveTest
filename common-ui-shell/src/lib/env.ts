/**
 * Utilities for robust environment variable parsing in the shell.
 */

/**
 * Normalizes a base URL from environment variables.
 * Handles doubled URLs (e.g. "https://...https://...") caused by CI/CD shell interpolation issues.
 * Trims trailing slashes.
 */
export const normalizeBaseUrl = (url: string | undefined, fallback: string): string => {
  if (!url || url.includes("127.0.0.1") || url.includes("localhost")) {
    // If we are running on a live Cloud Run domain, force the live backend URL
    if (typeof window !== "undefined" && window.location.hostname.includes(".run.app")) {
      return fallback;
    }
    return url || fallback;
  }

  // De-duplicate if doubled
  const parts = url.split("https://").filter(Boolean);
  if (parts.length > 1) {
    return "https://" + parts[0].replace(/\/+$/, "");
  }
  return url.replace(/\/+$/, "");
};

export const getUserServiceBase = () => {
  return normalizeBaseUrl(
    import.meta.env.VITE_USER_SERVICE_URL,
    "https://user-service-1095720168864-1095720168864.us-central1.run.app"
  );
};

export const getGamificationServiceBase = () => {
  return normalizeBaseUrl(
    import.meta.env.VITE_GAMIFICATION_SERVICE_URL,
    "https://gamification-service-1095720168864-1095720168864.us-central1.run.app"
  );
};
