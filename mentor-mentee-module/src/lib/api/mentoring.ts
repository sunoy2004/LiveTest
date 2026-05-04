import { mentoringPaths } from "@/config/mentoring";
import { MentoringApiError, mentoringJson } from "@/lib/api/client";
import type {
  MentoringProfileMeResponse,
  PostMenteeProfileBody,
  SchedulingBookBody,
  MentorshipRequestBody,
  MentorshipRequestHistoryRow,
  SearchResultItem,
  SearchRole,
} from "@/types/domain";

export async function getProfilesMe(): Promise<MentoringProfileMeResponse> {
  return mentoringJson<MentoringProfileMeResponse>(mentoringPaths.profilesMe, { method: "GET" });
}

/** GET /api/v1/profiles/mentor/{mentor_user_id} — public card (display_name from mentoring DB). */
export async function getMentorPublicDetail(mentorUserId: string): Promise<{ display_name?: string | null }> {
  return mentoringJson<{ display_name?: string | null }>(mentoringPaths.profilesMentor(mentorUserId), {
    method: "GET",
  });
}

export async function postMenteeProfile(body: PostMenteeProfileBody): Promise<void> {
  await mentoringJson(mentoringPaths.profilesMentee, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getSchedulingAvailability(mentorId: string): Promise<unknown> {
  return mentoringJson(mentoringPaths.schedulingAvailability(mentorId), { method: "GET" });
}

export async function postSchedulingBook(body: SchedulingBookBody): Promise<unknown> {
  return mentoringJson(mentoringPaths.schedulingBook, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getDashboardUpcomingSession(): Promise<unknown> {
  return mentoringJson(mentoringPaths.dashboardUpcomingSession, { method: "GET" });
}

export async function getDashboardGoals(): Promise<unknown> {
  return mentoringJson(mentoringPaths.dashboardGoals, { method: "GET" });
}

export async function getDashboardVault(): Promise<unknown> {
  return mentoringJson(mentoringPaths.dashboardVault, { method: "GET" });
}

export async function getSearch(
  q: string,
  role: Exclude<SearchRole, "all"> | "all" = "mentor",
  limit = 10,
): Promise<SearchResultItem[]> {
  const qs = new URLSearchParams({
    q,
    role,
    limit: String(limit),
  });
  return mentoringJson<SearchResultItem[]>(`${mentoringPaths.search}?${qs}`, { method: "GET" });
}

export async function postMentorshipRequest(body: MentorshipRequestBody): Promise<unknown> {
  return mentoringJson(mentoringPaths.requests, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getMentorshipRequestsIncoming(): Promise<unknown[]> {
  return mentoringJson(`${mentoringPaths.requests}/incoming`, { method: "GET" }) as Promise<unknown[]>;
}

export async function getMentorshipRequestsOutgoing(): Promise<unknown[]> {
  return mentoringJson(`${mentoringPaths.requests}/outgoing`, { method: "GET" }) as Promise<unknown[]>;
}

/**
 * When GET /requests/history is missing (older mentoring-service image — 404),
 * approximate history from /incoming + /outgoing (pending-focused; no timestamps).
 */
async function mentorshipHistoryLegacyFallback(): Promise<MentorshipRequestHistoryRow[]> {
  const [incomingRaw, outgoingRaw] = await Promise.all([
    getMentorshipRequestsIncoming(),
    getMentorshipRequestsOutgoing(),
  ]);
  const seen = new Set<string>();
  const rows: MentorshipRequestHistoryRow[] = [];

  for (const raw of incomingRaw as Record<string, unknown>[]) {
    const s = String(raw.sender_user_id ?? "");
    const r = String(raw.receiver_user_id ?? "");
    const key = `${s}|${r}`;
    if (!s || !r || seen.has(key)) continue;
    seen.add(key);
    rows.push({
      sender_user_id: s,
      receiver_user_id: r,
      status: String(raw.status ?? "PENDING"),
      intro_message: String(raw.intro_message ?? ""),
      created_at: null,
      mentee_name: String(raw.mentee_name ?? "Mentee"),
      mentor_name: "",
      you_are: "mentor",
    });
  }

  for (const raw of outgoingRaw as Record<string, unknown>[]) {
    const s = String(raw.sender_user_id ?? "");
    const r = String(raw.receiver_user_id ?? "");
    const key = `${s}|${r}`;
    if (!s || !r || seen.has(key)) continue;
    seen.add(key);
    rows.push({
      sender_user_id: s,
      receiver_user_id: r,
      status: String(raw.status ?? "PENDING"),
      intro_message: "",
      created_at: null,
      mentee_name: "",
      mentor_name: String(raw.mentor_name ?? "Mentor"),
      you_are: "mentee",
    });
  }

  return rows;
}

export async function getMentorshipRequestHistory(limit = 100): Promise<MentorshipRequestHistoryRow[]> {
  try {
    return await mentoringJson<MentorshipRequestHistoryRow[]>(mentoringPaths.requestsHistory(limit), {
      method: "GET",
    });
  } catch (e) {
    if (e instanceof MentoringApiError && e.status === 404) {
      return mentorshipHistoryLegacyFallback();
    }
    throw e;
  }
}

export async function putMentorshipRequestStatus(
  requestId: string,
  body: { status: "ACCEPTED" | "DECLINED" },
): Promise<unknown> {
  /** POST avoids proxies that mishandle PUT bodies; backend exposes PUT + POST on same path. */
  return mentoringJson(mentoringPaths.requestStatus(requestId), {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function postSessionHistory(
  sessionId: string,
  body: Record<string, unknown>,
): Promise<unknown> {
  return mentoringJson(mentoringPaths.sessionHistory(sessionId), {
    method: "POST",
    body: JSON.stringify(body),
  });
}
