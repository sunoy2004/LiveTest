import { Trophy } from "lucide-react";
import { Link } from "react-router-dom";
import SectionCard from "@/components/dashboard/SectionCard";
import type { LeaderboardItem } from "@/api/leaderboardApi";

export default function LeaderboardWidget({
  items,
  isLoading,
  isError,
}: {
  items: LeaderboardItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  return (
    <SectionCard
      title="Leaderboard"
      subtitle="Top lifetime credits earned"
      action={
        <div className="flex items-center gap-3">
          <Link to="leaderboard" className="text-xs text-muted-foreground hover:text-foreground">
            View more
          </Link>
          <Trophy className="h-4 w-4 text-muted-foreground" />
        </div>
      }
    >
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : isError ? (
        <p className="text-sm text-muted-foreground">Couldn’t load leaderboard.</p>
      ) : (items?.length ?? 0) === 0 ? (
        <p className="text-sm text-muted-foreground">No data yet.</p>
      ) : (
        <div className="space-y-2">
          {items!.slice(0, 10).map((r) => (
            <div
              key={r.user_id}
              className="flex items-center justify-between rounded-xl border border-border bg-background/40 px-3 py-2"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 text-sm font-semibold text-muted-foreground">#{r.rank}</div>
                <div className="truncate font-mono text-xs text-muted-foreground">{r.user_id}</div>
              </div>
              <div className="text-sm font-semibold">{r.score}</div>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

