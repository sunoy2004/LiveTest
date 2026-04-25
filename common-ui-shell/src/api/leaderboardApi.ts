export type LeaderboardItem = {
  rank: number;
  user_id: string;
  score: number;
};

import { normalizeBaseUrl } from "@/lib/env";

function getGamificationBase(): string {
  const base = import.meta.env.VITE_GAMIFICATION_SERVICE_URL as string | undefined;
  return normalizeBaseUrl(base, "http://localhost:8002");
}

export async function fetchLeaderboard(limit = 10): Promise<LeaderboardItem[]> {
  const res = await fetch(`${getGamificationBase()}/api/v1/leaderboard?limit=${encodeURIComponent(String(limit))}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as LeaderboardItem[];
}

