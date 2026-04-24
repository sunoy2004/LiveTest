import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";
import { fetchLeaderboard } from "@/api/leaderboardApi";

export function LeaderboardCard() {
  const q = useQuery({
    queryKey: ["gamification", "leaderboard", 10],
    queryFn: () => fetchLeaderboard(10),
    staleTime: 30_000,
  });

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Leaderboard</p>
            <p className="text-sm font-semibold text-foreground">Top lifetime earned</p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {q.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : q.isError ? (
          <p className="text-sm text-muted-foreground">Couldn’t load leaderboard.</p>
        ) : (q.data?.length ?? 0) === 0 ? (
          <p className="text-sm text-muted-foreground">No data yet.</p>
        ) : (
          q.data!.slice(0, 10).map((r) => (
            <div key={r.user_id} className="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
              <div className="flex min-w-0 items-center gap-3">
                <span className="w-8 text-sm font-semibold text-muted-foreground">#{r.rank}</span>
                <span className="truncate font-mono text-xs text-muted-foreground">{r.user_id}</span>
              </div>
              <span className="text-sm font-semibold text-foreground">{r.score}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

