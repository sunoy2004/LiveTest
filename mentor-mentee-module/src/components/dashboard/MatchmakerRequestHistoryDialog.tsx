import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { History, Loader2 } from "lucide-react";
import { getMentorshipRequestHistory } from "@/lib/api/mentoring";
import type { MentorshipRequestHistoryRow } from "@/types/domain";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

function statusBadgeClass(status: string): string {
  const s = status.toUpperCase();
  if (s === "PENDING") return "bg-warning/15 text-warning border-warning/30";
  if (s === "ACCEPTED") return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";
  if (s === "DECLINED") return "bg-destructive/15 text-destructive border-destructive/30";
  return "bg-muted text-muted-foreground border-border";
}

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "MMM d, yyyy · h:mm a");
  } catch {
    return iso;
  }
}

interface MatchmakerRequestHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token: string | null | undefined;
}

export default function MatchmakerRequestHistoryDialog({
  open,
  onOpenChange,
  token,
}: MatchmakerRequestHistoryDialogProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["user-service", "mentoring", "requests-history", token],
    queryFn: () => getMentorshipRequestHistory(100),
    enabled: Boolean(open && token),
    staleTime: 15_000,
  });

  const rows = data ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col gap-0 p-0 overflow-hidden sm:max-w-lg">
        <DialogHeader className="px-6 pt-6 pb-4 shrink-0 border-b border-border">
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-muted-foreground" />
            Matchmaking request history
          </DialogTitle>
          <DialogDescription>
            Rows from <span className="font-mono text-xs">mentorship_requests</span> where you sent or received a
            connection request. If the mentoring API is not yet on the latest version, this list may omit resolved
            requests and dates until you redeploy the mentoring service.
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {isLoading && (
            <div className="flex justify-center py-12 text-sm text-muted-foreground gap-2 items-center">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading…
            </div>
          )}
          {isError && (
            <div
              className="flex gap-2 rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground"
              role="status"
            >
              <span className="font-medium text-foreground shrink-0">Could not load history</span>
              <span className="text-xs leading-relaxed">
                {error instanceof Error ? error.message.slice(0, 320) : "Try again in a moment."}
              </span>
            </div>
          )}
          {!isLoading && !isError && rows.length === 0 && (
            <div className="text-center py-10 px-2">
              <p className="text-sm text-muted-foreground">No matchmaking requests yet.</p>
              <p className="text-xs text-muted-foreground/80 mt-2 max-w-sm mx-auto">
                Outgoing or incoming requests appear here after someone uses Connect on Matchmaker.
              </p>
            </div>
          )}
          {!isLoading && !isError && rows.length > 0 && (
            <ul className="space-y-3">
              {(rows as MentorshipRequestHistoryRow[]).map((r) => {
                const counterparty =
                  r.you_are === "mentee" ? r.mentor_name : r.mentee_name;
                const direction =
                  r.you_are === "mentee" ? "You → mentor" : "Mentee → you";
                return (
                  <li
                    key={`${r.sender_user_id}-${r.receiver_user_id}-${r.created_at ?? ""}`}
                    className="rounded-xl border border-border bg-card/60 px-3 py-3 text-sm shadow-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {formatWhen(r.created_at)}
                      </span>
                      <Badge
                        variant="outline"
                        className={cn("text-[10px] font-medium border", statusBadgeClass(r.status))}
                      >
                        {r.status}
                      </Badge>
                    </div>
                    <p className="mt-1.5 font-medium text-foreground">
                      {counterparty}
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">({direction})</span>
                    </p>
                    {(r.intro_message ?? "").trim() ? (
                      <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2 italic">
                        &ldquo;{r.intro_message.trim()}&rdquo;
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
