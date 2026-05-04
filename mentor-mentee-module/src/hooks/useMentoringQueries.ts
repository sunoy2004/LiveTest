import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getDashboardGoals,
  getDashboardUpcomingSession,
  getDashboardVault,
  getSearch,
  getProfilesMe,
  getMentorPublicDetail,
} from "@/lib/api/mentoring";
import { getRecommendations } from "@/lib/api/ai";
import { isAiApiConfigured, isMentoringApiConfigured } from "@/config/mentoring";
import type { AiRecommendationItem, MentoringProfileMeResponse, SearchRole } from "@/types/domain";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";

export const qk = {
  profileMe: ["mentoring", "profiles", "me"] as const,
  dashboardUpcoming: ["mentoring", "dashboard", "upcoming-session"] as const,
  dashboardGoals: ["mentoring", "dashboard", "goals"] as const,
  dashboardVault: ["mentoring", "dashboard", "vault"] as const,
  search: ["mentoring", "search"] as const,
  aiRecommendations: ["ai", "recommendations"] as const,
};

export function useMentoringProfileMe(enabled = isMentoringApiConfigured()) {
  return useQuery({
    queryKey: qk.profileMe,
    queryFn: () => getProfilesMe(),
    enabled,
  });
}

export function useDashboardUpcomingSession(enabled = isMentoringApiConfigured()) {
  return useQuery({
    queryKey: qk.dashboardUpcoming,
    queryFn: () => getDashboardUpcomingSession(),
    enabled,
  });
}

export function useDashboardGoals(enabled = isMentoringApiConfigured()) {
  return useQuery({
    queryKey: qk.dashboardGoals,
    queryFn: () => getDashboardGoals(),
    enabled,
  });
}

export function useDashboardVault(enabled = isMentoringApiConfigured()) {
  return useQuery({
    queryKey: qk.dashboardVault,
    queryFn: () => getDashboardVault(),
    enabled,
  });
}

export function useAiRecommendations(enabled = isAiApiConfigured()) {
  const { user } = useMentorShellAuth();
  const canEnrich = isMentoringApiConfigured();
  return useQuery({
    queryKey: [...qk.aiRecommendations, user?.id, canEnrich ? "enrich" : "raw"],
    queryFn: async (): Promise<AiRecommendationItem[]> => {
      const raw = await getRecommendations(user!.id);
      if (!canEnrich || !raw.length) return raw;
      const enriched = await Promise.all(
        raw.map(async (item): Promise<AiRecommendationItem> => {
          const existing = (item.display_name ?? "").trim();
          const looksSynthetic =
            !existing ||
            /^mentor\s+[0-9a-f-]{4,}/i.test(existing) ||
            /^user\s+[0-9a-f-]{4,}/i.test(existing);
          if (existing && !looksSynthetic) return item;
          try {
            const detail = await getMentorPublicDetail(item.mentor_id);
            const name = (detail?.display_name ?? "").trim();
            if (name) return { ...item, display_name: name };
          } catch {
            /* mentoring unreachable or 404 */
          }
          return item;
        }),
      );
      return enriched;
    },
    enabled: enabled && Boolean(user?.id),
  });
}

export function useMentoringSearch(
  q: string,
  role: SearchRole = "mentor",
  limit = 10,
  enabled = isMentoringApiConfigured(),
) {
  const query = q.trim();
  return useQuery({
    queryKey: [...qk.search, query, role, limit],
    queryFn: () => getSearch(query, role, limit),
    enabled: enabled && query.length > 0,
    staleTime: 10_000,
  });
}

export function useMentoringQueryInvalidation() {
  const qc = useQueryClient();
  return {
    invalidateProfile: () => qc.invalidateQueries({ queryKey: qk.profileMe }),
    invalidateDashboard: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: qk.dashboardUpcoming }),
        qc.invalidateQueries({ queryKey: qk.dashboardGoals }),
        qc.invalidateQueries({ queryKey: qk.dashboardVault }),
      ]),
    invalidateAi: () => qc.invalidateQueries({ queryKey: qk.aiRecommendations }),
  };
}

/**
 * Merge live GET /profiles/me with dev fallback only when mentoring API is not configured.
 * When the API is live, never inject fallback `mentee` — mentor-only users omit `mentee_profile`
 * and the old merge made the SPA think everyone had a mentee row (mentee UI).
 */
export function resolveProfile(
  data: MentoringProfileMeResponse | undefined,
  fallback: MentoringProfileMeResponse,
): MentoringProfileMeResponse {
  if (!data) return fallback;
  if (!isMentoringApiConfigured()) {
    return {
      is_admin: data.is_admin ?? false,
      mentee_profile: data.mentee_profile ?? fallback.mentee_profile,
      mentor_profile: data.mentor_profile ?? fallback.mentor_profile,
      mentee: data.mentee_profile ?? fallback.mentee_profile,
      mentor: data.mentor_profile ?? fallback.mentor_profile,
    };
  }
  return {
    is_admin: data.is_admin ?? false,
    mentee_profile: data.mentee_profile ?? data.mentee ?? undefined,
    mentor_profile: data.mentor_profile ?? data.mentor ?? undefined,
    mentee: data.mentee_profile ?? data.mentee ?? undefined,
    mentor: data.mentor_profile ?? data.mentor ?? undefined,
  };
}
