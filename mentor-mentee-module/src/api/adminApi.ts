import { getUserServiceBase } from "@/api/userService";

/** GET /admin/mentors — session pricing only (not wallet). */
export type AdminMentorRow = {
  id: string;
  name: string;
  email: string;
  tier: string;
  base_credit_override: number | null;
};

export type AdminMenteeRow = {
  id: string;
  name: string;
  email: string;
  status: string;
};

/** GET /admin/connections — mentor ↔ mentee links (read-only). */
export type AdminConnectionRow = {
  connection_id: string;
  mentor_profile_id: string;
  mentee_profile_id: string;
  mentor_user_id: string;
  mentee_user_id: string;
  mentor_email: string;
  mentee_email: string;
  status: string;
};

export type AdminSessionRow = {
  session_id: string;
  connection_id: string;
  mentor_name: string;
  mentee_name: string;
  start_time: string;
  status: string;
  price: number;
};

export type AdminDisputeRow = {
  id: string;
  status: string;
  kind: string;
  session_id: string | null;
  reason?: string | null;
  opened_by_user_id: string | null;
  created_at: string;
  resolved_at?: string | null;
  /** Credits charged for the linked session booking (mentee spend), when applicable. */
  credits_associated?: number | null;
};

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
    "Content-Type": "application/json",
  };
}

export async function fetchAdminMentors(token: string): Promise<AdminMentorRow[]> {
  const res = await fetch(`${getUserServiceBase()}/admin/mentors`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AdminMentorRow[]>;
}

export async function fetchAdminMentees(token: string): Promise<AdminMenteeRow[]> {
  const res = await fetch(`${getUserServiceBase()}/admin/mentees`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AdminMenteeRow[]>;
}

export async function fetchAdminConnections(token: string, limit = 500): Promise<AdminConnectionRow[]> {
  const q = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${getUserServiceBase()}/admin/connections?${q}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AdminConnectionRow[]>;
}

export async function fetchAdminSessions(token: string): Promise<AdminSessionRow[]> {
  const res = await fetch(`${getUserServiceBase()}/admin/sessions`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AdminSessionRow[]>;
}

export async function fetchAdminDisputes(token: string): Promise<AdminDisputeRow[]> {
  const res = await fetch(`${getUserServiceBase()}/admin/disputes`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AdminDisputeRow[]>;
}

export async function postResolveDispute(token: string, disputeId: string): Promise<void> {
  const res = await fetch(`${getUserServiceBase()}/admin/disputes/${encodeURIComponent(disputeId)}/resolve`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ resolution: "RESOLVED", refund_credits: 0 }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function putAdminMentorPricing(
  token: string,
  mentorProfileId: string,
  body: { tier: "TIER_1" | "TIER_2" | "TIER_3"; base_credit_override: number | null },
): Promise<{ mentor_profile_id: string; tier: string; base_credit_override: number | null }> {
  const res = await fetch(
    `${getUserServiceBase()}/admin/mentor/${encodeURIComponent(mentorProfileId)}`,
    {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    mentor_profile_id: string;
    tier: string;
    base_credit_override: number | null;
  }>;
}
