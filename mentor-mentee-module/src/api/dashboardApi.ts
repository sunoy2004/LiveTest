import type {
  DashboardStatsResponse,
  GoalItemResponse,
  UpcomingSessionItemResponse,
  UpcomingSessionResponse,
  VaultItemResponse,
} from "@/types/dashboard";
import { getUserServiceBase } from "@/api/userService";

function dashboardHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
  };
}

export async function fetchDashboardUpcoming(
  token: string,
  context: "mentor" | "mentee",
): Promise<UpcomingSessionResponse> {
  const q = new URLSearchParams({ context });
  const res = await fetch(`${getUserServiceBase()}/api/v1/dashboard/upcoming-session?${q}`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Upcoming session failed (${res.status})`);
  }
  return res.json() as Promise<UpcomingSessionResponse>;
}

export async function fetchDashboardUpcomingSessions(
  token: string,
  context: "mentor" | "mentee",
  limit = 5,
): Promise<UpcomingSessionItemResponse[]> {
  const q = new URLSearchParams({ context, limit: String(limit) });
  const res = await fetch(`${getUserServiceBase()}/api/v1/dashboard/upcoming-sessions?${q}`, {
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
  const q = new URLSearchParams({ context });
  const res = await fetch(`${getUserServiceBase()}/api/v1/dashboard/goals?${q}`, {
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
  const q = new URLSearchParams({ context });
  const res = await fetch(`${getUserServiceBase()}/api/v1/dashboard/vault?${q}`, {
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
  const q = new URLSearchParams({ context });
  const res = await fetch(`${getUserServiceBase()}/api/v1/dashboard/stats?${q}`, {
    headers: dashboardHeaders(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Dashboard stats failed (${res.status})`);
  }
  return res.json() as Promise<DashboardStatsResponse>;
}
