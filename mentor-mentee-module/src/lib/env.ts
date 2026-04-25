/**
 * Utilities for robust environment variable parsing in the Mentee UI.
 */

export const normalizeBaseUrl = (url: string | undefined, fallback: string): string => {
  if (!url || url.includes("127.0.0.1") || url.includes("localhost")) {
    if (typeof window !== "undefined" && window.location.hostname.includes(".run.app")) {
      return fallback;
    }
    return url || fallback;
  }
  const parts = url.split("https://").filter(Boolean);
  if (parts.length > 1) {
    return "https://" + parts[0].replace(/\/+$/, "");
  }
  return url.replace(/\/+$/, "");
};

export const getUserServiceBase = () => {
  return normalizeBaseUrl(
    import.meta.env.VITE_USER_SERVICE_URL,
    "https://user-service-1095720168864.us-central1.run.app"
  );
};

export const getMentoringServiceBase = () => {
  return normalizeBaseUrl(
    import.meta.env.VITE_MENTORING_API_BASE_URL,
    "https://user-service-1095720168864.us-central1.run.app"
  );
};
