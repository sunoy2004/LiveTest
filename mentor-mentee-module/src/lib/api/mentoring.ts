import { mentoringPaths } from "@/config/mentoring";
import { mentoringJson } from "@/lib/api/client";
import type {
  MentoringProfileMeResponse,
  PostMenteeProfileBody,
  SchedulingBookBody,
  MentorshipRequestBody,
  SearchResultItem,
  SearchRole,
} from "@/types/domain";

export async function getProfilesMe(): Promise<MentoringProfileMeResponse> {
  return mentoringJson<MentoringProfileMeResponse>(mentoringPaths.profilesMe, { method: "GET" });
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
