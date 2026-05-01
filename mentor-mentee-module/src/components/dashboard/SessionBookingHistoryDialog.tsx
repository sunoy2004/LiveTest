import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { History, Loader2 } from "lucide-react";
import { fetchSessionBookingLedger } from "@/api/dashboardApi";
import type { SessionBookingLedgerItem } from "@/types/dashboard";
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
  if (s === "APPROVED") return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";
  if (s === "REJECTED") return "bg-destructive/15 text-destructive border-destructive/30";
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

interface SessionBookingHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token: string | null | undefined;
}

export default function SessionBookingHistoryDialog({
  open,
  onOpenChange,
  token,
}: SessionBookingHistoryDialogProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["mentoring", "dashboard", "session-booking-requests", token],
    queryFn: () => fetchSessionBookingLedger(token!, 100),
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
            Session request history
          </DialogTitle>
          <DialogDescription>
            Records from mentoring <span className="font-mono text-xs">session_booking_requests</span>{" "}
            where you are the mentee or mentor.
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
              <p className="text-sm text-muted-foreground">No session booking requests yet.</p>
              <p className="text-xs text-muted-foreground/80 mt-2 max-w-sm mx-auto">
                When the <span className="font-mono">session_booking_requests</span> table has no rows for you, this
                list stays empty — that is normal until a mentee requests a slot.
              </p>
            </div>
          )}
          {!isLoading && !isError && rows.length > 0 && (
            <ul className="space-y-3">
              {rows.map((r: SessionBookingLedgerItem) => (
                <li
                  key={r.request_id}
                  className="rounded-xl border border-border bg-card/60 px-3 py-3 text-sm shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-foreground">{r.partner_name ?? "Partner"}</span>
                    <Badge
                      variant="outline"
                      className={cn("text-xs font-semibold uppercase tracking-wide", statusBadgeClass(r.status))}
                    >
                      {r.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1.5">
                    {r.viewer_role === "mentee" ? "You requested" : "Mentee requested"} ·{" "}
                    <span className="text-foreground/90">{formatWhen(r.requested_time)}</span>
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground/80 mt-1 truncate" title={r.request_id}>
                    id {r.request_id}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
