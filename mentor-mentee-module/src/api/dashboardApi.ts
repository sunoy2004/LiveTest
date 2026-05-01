import type {
  DashboardStatsResponse,
  GoalItemResponse,
  SessionBookingLedgerItem,
  UpcomingSessionItemResponse,
  UpcomingSessionResponse,
  VaultItemResponse,
} from "@/types/dashboard";
import { getMentoringApiBaseUrl, MENTORING_API_PREFIX } from "@/config/mentoring";
import { parseJsonListResponse } from "@/lib/api/jsonListResponse";

function dashboardHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
  };
}

const DASHBOARD_BASE = `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}/dashboard`;

export async function fetchDashboardUpcomingSessions(
  token: string,
  context: "mentor" | "mentee",
  limit = 5,
): Promise<UpcomingSessionItemResponse[]> {
  const q = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${DASHBOARD_BASE}/upcoming-sessions?${q}`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Upcoming sessions failed (${res.status})`);
  }
  return res.json() as Promise<UpcomingSessionItemResponse[]>;
}

export async function fetchDashboardGoals(
  token: string,
  context: "mentor" | "mentee",
): Promise<GoalItemResponse[]> {
  const res = await fetch(`${DASHBOARD_BASE}/goals`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Goals fetch failed (${res.status})`);
  }
  return res.json() as Promise<GoalItemResponse[]>;
}

/** POST /api/v1/dashboard/goals — add a personal quest / goal row in mentoring_db.goals */
export async function createDashboardGoal(
  token: string,
  title: string,
): Promise<GoalItemResponse> {
  const res = await fetch(`${DASHBOARD_BASE}/goals`, {
    method: "POST",
    headers: {
      ...dashboardHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title: title.trim() }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Could not create goal (${res.status})`);
  }
  return res.json() as Promise<GoalItemResponse>;
}

export async function fetchDashboardVault(
  token: string,
  context: "mentor" | "mentee",
): Promise<VaultItemResponse[]> {
  const res = await fetch(`${DASHBOARD_BASE}/vault`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Vault fetch failed (${res.status})`);
  }
  return res.json() as Promise<VaultItemResponse[]>;
}

export async function fetchDashboardStats(
  token: string,
  context: "mentor" | "mentee",
): Promise<DashboardStatsResponse> {
  const res = await fetch(`${DASHBOARD_BASE}/stats`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Dashboard stats failed (${res.status})`);
  }
  return res.json() as Promise<DashboardStatsResponse>;
}

export async function fetchSessionBookingLedger(
  token: string,
  limit = 100,
): Promise<SessionBookingLedgerItem[]> {
  const q = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${DASHBOARD_BASE}/session-booking-requests?${q}`, {
    headers: dashboardHeaders(token),
  });
  return parseJsonListResponse<SessionBookingLedgerItem>(res);
}
