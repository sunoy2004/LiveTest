import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Check, Clock, Eye, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getMentorshipRequestsIncoming, putMentorshipRequestStatus } from "@/lib/api/mentoring";
import { formatApiError } from "@/lib/api/errorMessage";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

/** GET /requests/incoming — mentor inbox; use sender_user_id for PUT /requests/{sender_user_id}/status */
export interface IncomingMatchmakerRequestRow {
  sender_user_id: string;
  receiver_user_id: string;
  status: string;
  mentee_name: string;
  intro_message?: string;
}

/** Mentee / sender id for PUT `/requests/{sender_user_id}/status` (supports alternate API keys). */
function menteeIdForStatusPut(r: IncomingMatchmakerRequestRow): string {
  const x = r as IncomingMatchmakerRequestRow & {
    mentee_user_id?: string;
    senderUserId?: string;
  };
  const raw = r.sender_user_id ?? x.mentee_user_id ?? x.senderUserId;
  return String(raw ?? "").trim();
}

interface IncomingMatchmakerRequestsPanelProps {
  token: string | null | undefined;
  enabled: boolean;
}

export default function IncomingMatchmakerRequestsPanel({
  token,
  enabled,
}: IncomingMatchmakerRequestsPanelProps) {
  const queryClient = useQueryClient();
  const [detail, setDetail] = useState<IncomingMatchmakerRequestRow | null>(null);
  
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["user-service", "mentoring", "incoming-matchmaker-requests", token],
    queryFn: () => getMentorshipRequestsIncoming(),
    enabled: Boolean(enabled && token),
    staleTime: 15_000,
  });

  if (!enabled || !token) return null;

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading connection requests…
      </div>
    );
  }

  const rows = (data as IncomingMatchmakerRequestRow[]) ?? [];
  if (rows.length === 0) {
    return (
      <p className="text-center py-8 text-sm text-muted-foreground">
        No pending connection requests.
      </p>
    );
  }

  const invalidateAfterDecision = () => {
    void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
    void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring", "requests-history"] });
    void queryClient.invalidateQueries({ queryKey: ["user-service", "dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["user-service", "dashboard", "stats"] });
    void queryClient.invalidateQueries({ queryKey: ["mentoring", "connected-mentors"] });
  };

  const handleReject = (r: IncomingMatchmakerRequestRow) => {
    void (async () => {
      const menteeId = menteeIdForStatusPut(r);
      if (!menteeId) {
        toast({
          title: "Could not decline",
          description: "Missing mentee id on this request row. Refresh the page.",
          variant: "destructive",
        });
        return;
      }
      try {
        await putMentorshipRequestStatus(menteeId, { status: "DECLINED" });
        toast({ title: "Request declined" });
        setDetail((d) => (d?.sender_user_id === r.sender_user_id ? null : d));
        invalidateAfterDecision();
      } catch (e) {
        toast({
          title: "Could not reject",
          description: formatApiError(e),
          variant: "destructive",
        });
      }
    })();
  };

  const handleAccept = (r: IncomingMatchmakerRequestRow) => {
    void (async () => {
      const menteeId = menteeIdForStatusPut(r);
      if (!menteeId) {
        toast({
          title: "Could not accept",
          description: "Missing mentee id on this request row. Refresh the page.",
          variant: "destructive",
        });
        return;
      }
      try {
        await putMentorshipRequestStatus(menteeId, { status: "ACCEPTED" });
        toast({ title: "Connection accepted", description: "You are now connected." });
        setDetail((d) => (d?.sender_user_id === r.sender_user_id ? null : d));
        invalidateAfterDecision();
      } catch (e) {
        toast({
          title: "Could not accept",
          description: formatApiError(e),
          variant: "destructive",
        });
      }
    })();
  };

  return (
    <>
      <div className="space-y-2">
        {rows.map((r) => (
          <div
            key={menteeIdForStatusPut(r) || r.mentee_name}
            className="flex flex-col gap-3 rounded-xl border border-border bg-card/50 p-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">{r.mentee_name}</p>
              <p className="text-xs text-muted-foreground line-clamp-2 italic text-ellipsis">
                {(r.intro_message ?? "").trim()
                  ? `“${(r.intro_message ?? "").trim()}”`
                  : "No introduction message."}
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:max-w-xl sm:flex-row sm:flex-wrap sm:justify-end">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="min-h-[44px] w-full gap-1.5 sm:min-h-9 sm:w-auto"
                disabled={isFetching}
                onClick={() => setDetail(r)}
              >
                <Eye className="h-3.5 w-3.5 shrink-0" />
                View
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="min-h-[44px] w-full gap-1.5 sm:min-h-9 sm:w-auto"
                disabled={isFetching}
                onClick={() => handleReject(r)}
              >
                <X className="h-3.5 w-3.5" /> Decline
              </Button>
              <Button
                type="button"
                size="sm"
                className="min-h-[44px] w-full gap-1.5 gradient-primary border-0 sm:min-h-9 sm:w-auto"
                disabled={isFetching}
                onClick={() => handleAccept(r)}
              >
                <Check className="h-3.5 w-3.5" /> Accept
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Dialog open={detail != null} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent
          className={cn(
            "flex max-h-[min(88dvh,88svh,40rem)] w-[calc(100vw-1rem)] max-w-lg flex-col gap-0 overflow-hidden p-0 sm:max-w-lg",
          )}
        >
          {detail ? (
            <>
              <DialogHeader className="shrink-0 space-y-1.5 border-b border-border/50 px-4 pb-4 pt-5 text-left sm:px-6">
                <DialogTitle className="pr-8 text-base leading-snug sm:text-lg">
                  Connection request
                </DialogTitle>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Mentee
                </p>
                <DialogDescription className="text-sm font-semibold text-foreground sm:text-base">
                  {detail.mentee_name}
                </DialogDescription>
              </DialogHeader>
              <div
                className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 py-4 sm:px-6 sm:py-5 [scrollbar-gutter:stable]"
                style={{ WebkitOverflowScrolling: "touch" }}
              >
                <dl className="space-y-3.5 text-sm">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Status
                    </dt>
                    <dd className="mt-1">
                      <Badge variant="outline" className="border-warning/30 bg-warning/10 text-warning">
                        Pending your decision
                      </Badge>
                    </dd>
                  </div>
                  <div>
                    <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Introduction Message
                    </dt>
                    <dd className="mt-1 text-foreground whitespace-pre-wrap rounded-md bg-muted/50 p-3 italic">
                      {(detail.intro_message ?? "").trim()
                        ? `“${(detail.intro_message ?? "").trim()}”`
                        : "No introduction message was provided."}
                    </dd>
                  </div>
                </dl>
              </div>
              <DialogFooter
                className={cn(
                  "shrink-0 flex-col gap-2 border-t border-border/50 px-4 py-4 sm:flex-row sm:justify-end sm:px-6",
                  "pb-[max(1rem,env(safe-area-inset-bottom))]",
                )}
              >
                <Button
                  type="button"
                  variant="outline"
                  className="min-h-[44px] w-full sm:w-auto"
                  disabled={isFetching}
                  onClick={() => handleReject(detail)}
                >
                  <X className="h-4 w-4 mr-1" /> Decline
                </Button>
                <Button
                  type="button"
                  className="min-h-[44px] w-full gap-1 gradient-primary border-0 sm:w-auto"
                  disabled={isFetching}
                  onClick={() => handleAccept(detail)}
                >
                  <Check className="h-4 w-4" /> Accept
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
