import { getUserServiceBase } from "@/api/userService";
import type {
  AvailableSlotItem,
  BookSessionSimpleResponse,
  ConnectedMentorItem,
  IncomingSessionRequestItem,
  MentorProfileDetail,
} from "@/types/userServiceMentoring";

function headers(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
    "Content-Type": "application/json",
  };
}

export async function fetchConnectedMentors(
  token: string,
): Promise<ConnectedMentorItem[]> {
  const res = await fetch(`${getUserServiceBase()}/api/v1/scheduling/connected-mentors`, {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `connected mentors failed (${res.status})`);
  }
  return res.json() as Promise<ConnectedMentorItem[]>;
}

export async function fetchMentorAvailability(
  token: string,
  mentorId: string,
): Promise<AvailableSlotItem[]> {
  const q = new URLSearchParams({ mentor_id: mentorId });
  const res = await fetch(`${getUserServiceBase()}/api/v1/scheduling/availability?${q}`, {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `availability failed (${res.status})`);
  }
  return res.json() as Promise<AvailableSlotItem[]>;
}

export async function fetchMentorProfileDetail(
  token: string,
  mentorProfileId: string,
): Promise<MentorProfileDetail> {
  const res = await fetch(
    `${getUserServiceBase()}/api/v1/profiles/mentor/${encodeURIComponent(mentorProfileId)}`,
    { headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `mentor profile failed (${res.status})`);
  }
  return res.json() as Promise<MentorProfileDetail>;
}

export async function bookSessionSimple(
  token: string,
  body: { connection_id: string; slot_id: string },
): Promise<BookSessionSimpleResponse> {
  const res = await fetch(`${getUserServiceBase()}/api/v1/scheduling/book`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `book failed (${res.status})`);
  }
  return res.json() as Promise<BookSessionSimpleResponse>;
}

export async function fetchIncomingSessionRequests(
  token: string,
): Promise<IncomingSessionRequestItem[]> {
  const res = await fetch(`${getUserServiceBase()}/api/v1/sessions/incoming-requests`, {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `incoming requests failed (${res.status})`);
  }
  return res.json() as Promise<IncomingSessionRequestItem[]>;
}

export async function acceptSessionRequest(
  token: string,
  requestId: string,
): Promise<{ session_id: string; status: string; meeting_url: string | null; start_time: string }> {
  const res = await fetch(
    `${getUserServiceBase()}/api/v1/sessions/requests/${encodeURIComponent(requestId)}/accept`,
    { method: "POST", headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `accept failed (${res.status})`);
  }
  return res.json() as Promise<{
    session_id: string;
    status: string;
    meeting_url: string | null;
    start_time: string;
  }>;
}

export async function rejectSessionRequest(token: string, requestId: string): Promise<void> {
  const res = await fetch(
    `${getUserServiceBase()}/api/v1/sessions/requests/${encodeURIComponent(requestId)}/reject`,
    { method: "POST", headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `reject failed (${res.status})`);
  }
}

