export type LeaderboardItem = {
  rank: number;
  user_id: string;
  score: number;
};

function getGamificationBase(): string {
  const g = import.meta.env.VITE_GAMIFICATION_SERVICE_URL as string | undefined;
  const legacy = import.meta.env.VITE_CREDIT_SERVICE_URL as string | undefined;
  const base = g ?? legacy ?? "";
  return base.replace(/\/$/, "");
}

export async function fetchLeaderboard(limit = 10): Promise<LeaderboardItem[]> {
  const res = await fetch(`${getGamificationBase()}/api/v1/leaderboard?limit=${encodeURIComponent(String(limit))}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as LeaderboardItem[];
}

