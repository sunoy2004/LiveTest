import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getDashboardGoals,
  getDashboardUpcomingSession,
  getDashboardVault,
  getSearch,
  getProfilesMe,
} from "@/lib/api/mentoring";
import { getRecommendations } from "@/lib/api/ai";
import { isAiApiConfigured, isMentoringApiConfigured } from "@/config/mentoring";
import type { MentoringProfileMeResponse, SearchRole } from "@/types/domain";
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
  return useQuery({
    queryKey: [...qk.aiRecommendations, user?.id],
    queryFn: () => getRecommendations(user!.id),
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

/** Merge live profile with optional static fallback for dev. */
export function resolveProfile(
  data: MentoringProfileMeResponse | undefined,
  fallback: MentoringProfileMeResponse,
): MentoringProfileMeResponse {
  if (!data) return fallback;
  return {
    mentee: data.mentee ?? fallback.mentee,
    mentor: data.mentor ?? fallback.mentor,
  };
}
