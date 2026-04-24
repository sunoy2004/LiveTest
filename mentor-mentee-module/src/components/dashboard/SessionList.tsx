import { useState } from "react";
import { format, parseISO } from "date-fns";
import { Session } from "@/data/mockData";
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
import { Video, Calendar, ArrowRight, Clock, Star, FileText, ChevronDown, ChevronUp, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface SessionListProps {
  sessions: Session[];
  type: "upcoming" | "history";
  /** Drives labels in the details overlay (mentor sees mentee-focused copy). */
  viewerRole?: "mentor" | "mentee";
  emptyTitle?: string;
  emptySubtitle?: string;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  upcoming: { label: "Scheduled", className: "bg-success/10 text-success border-success/20" },
  pending_approval: {
    label: "Pending approval",
    className: "bg-warning/10 text-warning border-warning/20",
  },
  rejected: { label: "Rejected", className: "bg-destructive/10 text-destructive border-destructive/20" },
  pending_payment: { label: "Pending Payment", className: "bg-warning/10 text-warning border-warning/20" },
  in_progress: { label: "Live", className: "bg-primary/10 text-primary border-primary/20" },
  completed: { label: "Completed", className: "bg-success/10 text-success border-success/20" },
  missed: { label: "Missed", className: "bg-destructive/10 text-destructive border-destructive/20" },
};

const formatCountdown = (minutes?: number) => {
  if (!minutes) return null;
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  return `${Math.floor(minutes / 1440)}d`;
};

function formatWhenLong(session: Session): string {
  if (session.startTimeIso) {
    try {
      return format(parseISO(session.startTimeIso), "EEEE, MMMM d, yyyy · h:mm a");
    } catch {
      /* fall through */
    }
  }
  return `${session.date} · ${session.time}`;
}

const SessionList = ({
  sessions,
  type,
  viewerRole = "mentee",
  emptyTitle,
  emptySubtitle,
}: SessionListProps) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [upcomingDetail, setUpcomingDetail] = useState<Session | null>(null);

  if (sessions.length === 0) {
    const title =
      emptyTitle ??
      `No sessions ${type === "upcoming" ? "scheduled" : "recorded"}`;
    const subtitle = emptySubtitle ?? "Your sessions will appear here";
    return (
      <div className="text-center py-10 text-muted-foreground">
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
          <Calendar className="h-5 w-5 opacity-50" />
        </div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs mt-1">{subtitle}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sessions.map((session, i) => {
        const config = statusConfig[session.status] || statusConfig.upcoming;
        const countdown = formatCountdown(session.startsInMinutes);
        const isExpanded = expandedId === session.id;
        const hasMeetLink = Boolean(session.meetingUrl);
        const canJoin = session.status === "upcoming" && hasMeetLink;
        const partnerInitials = (session.partnerName || "?")
          .split(/\s+/)
          .filter(Boolean)
          .map((n) => n[0])
          .join("")
          .slice(0, 3);

        return (
          <div
            key={session.id}
            className={cn(
              "group rounded-xl border border-transparent transition-all duration-200",
              "hover:bg-accent/50 animate-fade-in",
              isExpanded && "bg-accent/30 border-border"
            )}
            style={{ animationDelay: `${i * 60}ms`, animationFillMode: "backwards" }}
          >
            <div
              className={cn(
                "flex flex-col gap-3 py-3 px-3.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4",
                type === "upcoming" && "touch-manipulation",
              )}
            >
              <div
                role={type === "upcoming" ? "button" : undefined}
                tabIndex={type === "upcoming" ? 0 : undefined}
                className={cn(
                  "flex min-h-[48px] flex-1 items-center gap-3 min-w-0 text-left rounded-lg -m-1 p-1",
                  type === "upcoming" &&
                    "cursor-pointer active:bg-accent/70 sm:min-h-0 sm:cursor-pointer",
                  type === "history" && "cursor-pointer",
                )}
                onClick={() => {
                  if (type === "history") {
                    setExpandedId(isExpanded ? null : session.id);
                  } else if (type === "upcoming") {
                    setUpcomingDetail(session);
                  }
                }}
                onKeyDown={(e) => {
                  if (type !== "upcoming") return;
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setUpcomingDetail(session);
                  }
                }}
                aria-label={
                  type === "upcoming"
                    ? `View details for session with ${session.partnerName}`
                    : undefined
                }
              >
                <div className="h-10 w-10 shrink-0 rounded-full gradient-primary flex items-center justify-center shadow-sm shadow-primary/20">
                  <span className="text-xs font-bold text-primary-foreground">{partnerInitials}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-foreground truncate">{session.partnerName}</p>
                    <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0 h-5 border", config.className)}>
                      {config.label}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">{session.date}</span> · {session.time}
                      {type === "upcoming" ? (
                        <> · Mentoring session</>
                      ) : (
                        <> · {session.topic}</>
                      )}
                    </p>
                    {countdown && type === "upcoming" && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded-full">
                        <Clock className="h-2.5 w-2.5" /> {countdown}
                      </span>
                    )}
                  </div>
                  {type === "upcoming" && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground sm:hidden">
                      <Info className="h-3 w-3 shrink-0 opacity-70" />
                      Tap for details
                    </p>
                  )}
                </div>
              </div>

              <div className="flex w-full shrink-0 items-center justify-end gap-2 sm:w-auto sm:ml-0">
                {type === "upcoming" ? (
                  <Button
                    type="button"
                    size="sm"
                    disabled={!canJoin}
                    className={cn(
                      "w-full min-h-[44px] sm:min-h-0 sm:w-auto gradient-primary border-0 shadow-sm shadow-primary/20 transition-shadow",
                      !canJoin && "opacity-50 cursor-not-allowed",
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (session.meetingUrl) {
                        window.open(session.meetingUrl, "_blank", "noopener,noreferrer");
                      }
                    }}
                  >
                    <Video className="h-3.5 w-3.5 mr-1" />
                    {canJoin ? "Join" : "No link"}
                    {canJoin && <ArrowRight className="h-3 w-3 ml-0.5 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />}
                  </Button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    {session.rating && (
                      <span className="flex items-center gap-0.5 text-xs text-warning">
                        <Star className="h-3 w-3 fill-warning" /> {session.rating}
                      </span>
                    )}
                    {session.notes && <FileText className="h-3.5 w-3.5 text-muted-foreground" />}
                    {type === "history" && (
                      isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Expandable vault details */}
            {isExpanded && type === "history" && (
              <div className="px-3.5 pb-3 animate-fade-in">
                <div className="ml-[52px] p-3 rounded-lg bg-muted/50 border border-border space-y-2 text-xs">
                  {session.feedback && (
                    <div>
                      <span className="font-semibold text-foreground">Feedback:</span>
                      <span className="text-muted-foreground ml-1">{session.feedback}</span>
                    </div>
                  )}
                  {session.notes && (
                    <div>
                      <span className="font-semibold text-foreground">Notes:</span>
                      <span className="text-muted-foreground ml-1">{session.notes}</span>
                    </div>
                  )}
                  {(session.mentorRating != null || session.menteeRating != null) && (
                    <div className="space-y-1">
                      {session.mentorRating != null && (
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-foreground">Mentor rating:</span>
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star
                              key={`m-${i}`}
                              className={cn(
                                "h-3 w-3",
                                i < session.mentorRating! ? "fill-warning text-warning" : "text-muted",
                              )}
                            />
                          ))}
                        </div>
                      )}
                      {session.menteeRating != null && (
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-foreground">Mentee rating:</span>
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star
                              key={`e-${i}`}
                              className={cn(
                                "h-3 w-3",
                                i < session.menteeRating! ? "fill-warning text-warning" : "text-muted",
                              )}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {session.rating != null &&
                    session.mentorRating == null &&
                    session.menteeRating == null && (
                    <div className="flex items-center gap-1">
                      <span className="font-semibold text-foreground">Rating:</span>
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} className={cn("h-3 w-3", i < session.rating! ? "fill-warning text-warning" : "text-muted")} />
                      ))}
                    </div>
                  )}
                  {session.costCredits && (
                    <div>
                      <span className="font-semibold text-foreground">Cost:</span>
                      <span className="text-muted-foreground ml-1">{session.costCredits} credits</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}

      <Dialog open={upcomingDetail != null} onOpenChange={(open) => !open && setUpcomingDetail(null)}>
        <DialogContent
          className={cn(
            "flex min-h-0 w-[calc(100vw-1rem)] max-w-lg flex-col gap-0 overflow-hidden p-0 sm:w-full sm:max-w-lg",
            "max-h-[min(88dvh,88svh,40rem)]",
          )}
        >
          {upcomingDetail ? (
            <>
              <DialogHeader className="shrink-0 space-y-1.5 border-b border-border/50 px-4 pb-4 pt-5 text-left sm:px-6">
                <DialogTitle className="pr-8 text-base leading-snug sm:text-lg">
                  Session details
                </DialogTitle>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {viewerRole === "mentor" ? "Mentee" : "Mentor"}
                </p>
                <DialogDescription className="text-sm font-semibold text-foreground sm:text-base">
                  {upcomingDetail.partnerName}
                </DialogDescription>
              </DialogHeader>
              <div
                className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-4 sm:px-6 sm:py-5 [scrollbar-gutter:stable]"
                style={{ WebkitOverflowScrolling: "touch" }}
              >
                <dl className="space-y-3.5 text-sm">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Status</dt>
                    <dd className="mt-1">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px] border",
                          statusConfig[upcomingDetail.status]?.className ?? statusConfig.upcoming.className,
                        )}
                      >
                        {statusConfig[upcomingDetail.status]?.label ?? "Scheduled"}
                      </Badge>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {upcomingDetail.status === "upcoming" ? "Scheduled" : "Requested time"}
                    </dt>
                    <dd className="mt-0.5 text-foreground">{formatWhenLong(upcomingDetail)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Session</dt>
                    <dd className="mt-0.5 text-foreground">{upcomingDetail.topic}</dd>
                  </div>
                  {typeof upcomingDetail.costCredits === "number" && upcomingDetail.costCredits > 0 ? (
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Credits</dt>
                      <dd className="mt-0.5 font-medium tabular-nums text-foreground">
                        {upcomingDetail.costCredits} credits
                      </dd>
                    </div>
                  ) : null}
                  {upcomingDetail.startsInMinutes != null && upcomingDetail.startsInMinutes > 0 ? (
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Starts in</dt>
                      <dd className="mt-0.5 inline-flex items-center gap-1.5 text-foreground">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        {formatCountdown(upcomingDetail.startsInMinutes) ?? "—"}
                      </dd>
                    </div>
                  ) : null}
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {upcomingDetail.id.startsWith("req:") ? "Request id" : "Session id"}
                    </dt>
                    <dd className="mt-0.5 break-all font-mono text-xs text-muted-foreground">
                      {upcomingDetail.id.startsWith("req:") ? upcomingDetail.id.slice(4) : upcomingDetail.id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Meeting</dt>
                    <dd className="mt-0.5 break-all text-xs text-foreground">
                      {upcomingDetail.meetingUrl ? (
                        <a
                          href={upcomingDetail.meetingUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary underline-offset-4 hover:underline"
                        >
                          {upcomingDetail.meetingUrl}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">Link not available yet</span>
                      )}
                    </dd>
                  </div>
                </dl>
              </div>
              <DialogFooter
                className={cn(
                  "shrink-0 border-t border-border/50 px-4 py-4 sm:px-6",
                  "pb-[max(1rem,env(safe-area-inset-bottom))]",
                )}
              >
                <Button
                  type="button"
                  variant={upcomingDetail.status === "upcoming" ? "default" : "secondary"}
                  className={cn(
                    "min-h-[48px] w-full gap-2 sm:min-h-10 sm:w-auto",
                    upcomingDetail.status === "upcoming" &&
                      "gradient-primary border-0 shadow-sm shadow-primary/20",
                  )}
                  disabled={
                    upcomingDetail.status === "upcoming" && !upcomingDetail.meetingUrl
                  }
                  onClick={() => {
                    if (upcomingDetail.status === "upcoming" && upcomingDetail.meetingUrl) {
                      window.open(upcomingDetail.meetingUrl, "_blank", "noopener,noreferrer");
                    } else {
                      setUpcomingDetail(null);
                    }
                  }}
                >
                  <Video className="h-4 w-4" />
                  {upcomingDetail.status === "upcoming" ? "Join meeting" : "Close"}
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SessionList;
