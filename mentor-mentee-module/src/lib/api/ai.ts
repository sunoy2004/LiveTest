import { aiPaths } from "@/config/mentoring";
import { aiJson } from "@/lib/api/client";
import type { AiRecommendationItem } from "@/types/domain";

/** Workflow 2 — AI Graph / Matching service (requires user_id + Bearer). */
export async function getRecommendations(
  userId: string,
): Promise<AiRecommendationItem[]> {
  const q = new URLSearchParams({ user_id: userId, limit: "10" });
  const data = await aiJson<AiRecommendationItem[] | { items?: AiRecommendationItem[] }>(
    `${aiPaths.recommendations}?${q}`,
    { method: "GET" },
  );
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object" && "items" in data && Array.isArray(data.items)) {
    return data.items;
  }
  return [];
}

/** Record reject / success signal for hybrid scoring and exclusion (Bearer = mentee). */
export async function postRecommendationFeedback(body: {
  target_user_id: string;
  interaction_type: "REJECTED_SUGGESTION" | "SUCCESSFUL_MENTORSHIP";
}): Promise<unknown> {
  return aiJson(aiPaths.recommendationsFeedback, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
