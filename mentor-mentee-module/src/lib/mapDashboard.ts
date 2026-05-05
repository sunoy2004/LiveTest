import type {
  GoalItemResponse,
  UpcomingSessionItemResponse,
  UpcomingSessionResponse,
  VaultItemResponse,
} from "@/types/dashboard";
import type { Goal, Session } from "@/data/mockData";

function formatSessionWhen(iso: string): { dateLabel: string; timeLabel: string; startsInMinutes: number } {
  const start = new Date(iso);
  const now = new Date();
  const diffMs = start.getTime() - now.getTime();
  const startsInMinutes = Math.max(0, Math.floor(diffMs / 60_000));

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const msPerDay = 86400000;
  const dayDiff = Math.round((day.getTime() - today.getTime()) / msPerDay);

  let dateLabel: string;
  if (dayDiff === 0) dateLabel = "Today";
  else if (dayDiff === 1) dateLabel = "Tomorrow";
  else if (dayDiff === -1) dateLabel = "Yesterday";
  else {
    dateLabel = start.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  const timeLabel = start.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });

  return { dateLabel, timeLabel, startsInMinutes };
}

function notesSummary(notes: Record<string, unknown>): string {
  const summary = notes.summary;
  if (typeof summary === "string" && summary.trim()) return summary;
  try {
    return JSON.stringify(notes, null, 2);
  } catch {
    return "";
  }
}

function averageRating(a: number | null | undefined, b: number | null | undefined): number | undefined {
  const nums = [a, b].filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
  if (nums.length === 0) return undefined;
  const sum = nums.reduce((s, x) => s + x, 0);
  return Math.round((sum / nums.length) * 10) / 10;
}

function mapDashboardStatus(apiStatus: string | null | undefined): Session["status"] {
  const u = (apiStatus ?? "").toUpperCase();
  if (u === "PENDING" || u === "PENDING_APPROVAL") return "pending_approval";
  if (u === "REJECTED") return "rejected";
  if (u === "SCHEDULED") return "upcoming";
  return "upcoming";
}

export function mapUpcomingSessions(res: UpcomingSessionResponse): Session[] {
  if (!res.start_time || (!res.session_id && !res.booking_request_id)) return [];
  const s = res;
  const { dateLabel, timeLabel, startsInMinutes } = formatSessionWhen(s.start_time);
  const cost = s.price ?? s.session_credit_cost ?? 0;
  const id = s.session_id ?? `req:${s.booking_request_id}`;
  return [
    {
      id,
      partnerName: s.partner_name ?? "Partner",
      partnerAvatar: "",
      date: dateLabel,
      time: timeLabel,
      topic: "Mentoring session",
      status: mapDashboardStatus(s.status),
      startsInMinutes,
      meetingUrl: s.meeting_url ?? undefined,
      costCredits: cost,
      startTimeIso: s.start_time,
      meetingNotes: typeof s.meeting_notes === "string" ? s.meeting_notes : undefined,
      meetingOutcome: typeof s.meeting_outcome === "string" ? s.meeting_outcome : undefined,
    },
  ];
}

export function mapUpcomingSessionList(items: UpcomingSessionItemResponse[]): Session[] {
  return items
    .filter((s) => {
      const sid = (s.session_id ?? "").trim();
      const bid = (s.booking_request_id ?? "").trim();
      const hasId = Boolean(sid || bid);
      const hasTime = typeof s.start_time === "string" && s.start_time.trim().length > 0;
      return hasId && hasTime;
    })
    .map((s) => {
      const { dateLabel, timeLabel, startsInMinutes } = formatSessionWhen(s.start_time);
      const cost = s.price ?? s.session_credit_cost ?? 0;
      const id = s.session_id ?? `req:${s.booking_request_id}`;
      return {
        id,
        partnerName: s.partner_name ?? "Partner",
        partnerAvatar: "",
        date: dateLabel,
        time: timeLabel,
        topic: "Mentoring session",
        status: mapDashboardStatus(s.status),
        startsInMinutes,
        meetingUrl: s.meeting_url ?? undefined,
        costCredits: cost,
        startTimeIso: s.start_time,
        meetingNotes: typeof s.meeting_notes === "string" ? s.meeting_notes : undefined,
        meetingOutcome: typeof s.meeting_outcome === "string" ? s.meeting_outcome : undefined,
      };
    });
}

export function mapGoals(items: GoalItemResponse[]): Goal[] {
  return items.map((g, i) => {
    const progress = g.status === "COMPLETED" ? 100 : 40 + (i % 5) * 10;
    return {
      id: g.id,
      title: g.title,
      progress,
      xpReward: 300,
      category: g.status === "COMPLETED" ? "Completed" : "Active",
    };
  });
}

export function mapVaultSessions(items: VaultItemResponse[]): Session[] {
  return items.map((v) => {
    const { dateLabel, timeLabel } = formatSessionWhen(v.start_time);
    const notes = notesSummary(v.notes ?? {});
    return {
      id: v.session_id,
      partnerName: v.partner_name ?? "Partner",
      partnerAvatar: "",
      date: dateLabel,
      time: timeLabel,
      topic: "Session recap",
      status: "completed",
      notes,
      rating: averageRating(v.mentor_rating, v.mentee_rating),
      mentorRating: v.mentor_rating ?? undefined,
      menteeRating: v.mentee_rating ?? undefined,
      meetingNotes: typeof v.meeting_notes === "string" ? v.meeting_notes : undefined,
      meetingOutcome: typeof v.meeting_outcome === "string" ? v.meeting_outcome : undefined,
    };
  });
}
