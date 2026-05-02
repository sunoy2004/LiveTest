import { getMentoringApiBaseUrl, MENTORING_API_PREFIX } from "@/config/mentoring";
import { parseJsonListResponse } from "@/lib/api/jsonListResponse";
import type {
  AvailableSlotItem,
  BookSessionSimpleResponse,
  ConnectedMentorItem,
  IncomingSessionRequestItem,
  MentorProfileDetail,
} from "@/types/userServiceMentoring";

function mentoringV1(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}${p}`;
}

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
  const res = await fetch(mentoringV1("/scheduling/connected-mentors"), {
    headers: headers(token),
  });
  return parseJsonListResponse<ConnectedMentorItem>(res);
}

export async function fetchMentorAvailability(
  token: string,
  mentorId: string,
): Promise<AvailableSlotItem[]> {
  const q = new URLSearchParams({ mentor_id: mentorId });
  const res = await fetch(`${mentoringV1("/scheduling/availability")}?${q}`, {
    headers: headers(token),
  });
  return parseJsonListResponse<AvailableSlotItem>(res);
}

export async function fetchMentorProfileDetail(
  token: string,
  mentorProfileId: string,
): Promise<MentorProfileDetail> {
  const res = await fetch(
    `${mentoringV1("/profiles/mentor")}/${encodeURIComponent(mentorProfileId)}`,
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
  const res = await fetch(mentoringV1("/scheduling/book"), {
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
  const res = await fetch(mentoringV1("/sessions/incoming-requests"), {
    headers: headers(token),
  });
  return parseJsonListResponse<IncomingSessionRequestItem>(res);
}

export async function acceptSessionRequest(
  token: string,
  requestId: string,
): Promise<{ session_id: string; status: string; meeting_url: string | null; start_time: string }> {
  const res = await fetch(
    `${mentoringV1("/sessions/requests")}/${encodeURIComponent(requestId)}/accept`,
    { method: "POST", headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    let msg = err || `accept failed (${res.status})`;
    try {
      const j = JSON.parse(err) as { detail?: string };
      if (typeof j.detail === "string" && j.detail.trim()) msg = j.detail;
    } catch {
      /* use raw body */
    }
    throw new Error(msg);
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
    `${mentoringV1("/sessions/requests")}/${encodeURIComponent(requestId)}/reject`,
    { method: "POST", headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `reject failed (${res.status})`);
  }
}


export async function fetchMyAvailability(token: string): Promise<AvailableSlotItem[]> {
  const res = await fetch(mentoringV1("/scheduling/my-availability"), {
    headers: headers(token),
  });
  return parseJsonListResponse<AvailableSlotItem>(res);
}


export async function addAvailability(
  token: string,
  body: { start_time: string; end_time: string },
): Promise<{ slot_id: string; status: string }> {
  const res = await fetch(mentoringV1("/scheduling/availability"), {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `add availability failed (${res.status})`);
  }
  return res.json() as Promise<{ slot_id: string; status: string }>;
}


export async function deleteAvailability(token: string, slotId: string): Promise<void> {
  const res = await fetch(
    `${mentoringV1("/scheduling/availability")}/${encodeURIComponent(slotId)}`,
    { method: "DELETE", headers: headers(token) },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `delete availability failed (${res.status})`);
  }
}

export async function updateAvailability(
  token: string,
  slotId: string,
  body: { start_time: string; end_time: string },
): Promise<{ slot_id: string; status: string }> {
  const res = await fetch(
    `${mentoringV1("/scheduling/availability")}/${encodeURIComponent(slotId)}`,
    {
      method: "PATCH",
      headers: headers(token),
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `update availability failed (${res.status})`);
  }
  return res.json() as Promise<{ slot_id: string; status: string }>;
}

