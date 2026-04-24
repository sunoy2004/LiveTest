import { useMemo } from "react";
import { useLocation } from "react-router-dom";

/** Resolves `/mentoring/admin` or `/admin` from current path for federated / standalone. */
export function useAdminRoot(): string {
  const { pathname } = useLocation();
  return useMemo(() => {
    const idx = pathname.indexOf("/admin");
    if (idx >= 0) {
      return pathname.slice(0, idx + "/admin".length);
    }
    return "/admin";
  }, [pathname]);
}
