import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowLeft, Trophy } from "lucide-react";
import SectionCard from "@/components/dashboard/SectionCard";
import { fetchLeaderboard } from "@/api/leaderboardApi";

export default function LeaderboardPage() {
  const q = useQuery({
    queryKey: ["gamification", "leaderboard", 50],
    queryFn: () => fetchLeaderboard(50),
    staleTime: 30_000,
  });

  return (
    <div className="w-full min-h-0 space-y-6 p-4 sm:p-6 md:p-8 pb-16 sm:pb-20 md:pb-24">
      <div className="flex items-center gap-3">
        <Link to=".." className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <h1 className="text-lg font-semibold">Leaderboard</h1>
      </div>

      <SectionCard
        title="Top earners"
        subtitle="Ranked by lifetime credits earned"
        action={<Trophy className="h-4 w-4 text-muted-foreground" />}
      >
        {q.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : q.isError ? (
          <p className="text-sm text-muted-foreground">Couldn’t load leaderboard.</p>
        ) : (
          <div className="space-y-2">
            {q.data!.map((r) => (
              <div
                key={r.user_id}
                className="flex items-center justify-between rounded-xl border border-border bg-background/40 px-3 py-2"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 text-sm font-semibold text-muted-foreground">#{r.rank}</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">{r.user_id}</div>
                </div>
                <div className="text-sm font-semibold">{r.score}</div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

