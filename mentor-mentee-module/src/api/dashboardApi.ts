import type {
  DashboardStatsResponse,
  GoalItemResponse,
  UpcomingSessionItemResponse,
  UpcomingSessionResponse,
  VaultItemResponse,
} from "@/types/dashboard";
import { getMentoringApiBaseUrl, MENTORING_API_PREFIX } from "@/config/mentoring";

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
