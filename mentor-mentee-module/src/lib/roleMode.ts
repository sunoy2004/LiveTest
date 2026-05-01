import type {
  UserServiceMenteeProfile,
  UserServiceMentorProfile,
} from "@/types/userServiceProfile";

export type RoleUiMode = {
  /** Single effective dashboard role; when both profiles exist, default starting tab. */
  defaultRole: "mentor" | "mentee";
  /** Show mentor/mentee toggle only when user has both domain profiles. */
  showRoleToggle: boolean;
};

function normalizeJwtRoles(roles?: string[] | null): string[] {
  if (!roles?.length) return [];
  return roles.map((r) => String(r).trim().toUpperCase()).filter(Boolean);
}

/**
 * When mentoring profiles are ambiguous or still loading, prefer JWT `role` from User Service
 * (`MENTOR` / `MENTEE` / `ADMIN` in `users.role` array).
 */
export function inferDashboardRoleFromJwt(roles?: string[] | null): "mentor" | "mentee" | null {
  const r = new Set(normalizeJwtRoles(roles));
  const hasMentor = r.has("MENTOR");
  const hasMentee = r.has("MENTEE");
  if (hasMentor && !hasMentee) return "mentor";
  if (hasMentee && !hasMentor) return "mentee";
  if (hasMentor && hasMentee) return "mentor";
  return null;
}

/**
 * While GET /profiles/me is loading. Prefer JWT roles so mentor-only users do not flash mentee UI.
 */
export function getRoleUiModeWhileProfileLoading(shellRoles?: string[] | null): RoleUiMode {
  const fromJwt = inferDashboardRoleFromJwt(shellRoles);
  return { defaultRole: fromJwt ?? "mentee", showRoleToggle: false };
}

/**
 * Domain profiles are the source of truth for mentoring UI.
 * - Only mentor profile → mentor dashboard, no toggle
 * - Only mentee profile → mentee dashboard, no toggle
 * - Both → toggle; default from JWT when possible, else mentee
 * - Neither → JWT hint, else mentee
 */
export function getRoleUiModeFromProfiles(
  mentor: UserServiceMentorProfile | null | undefined,
  mentee: UserServiceMenteeProfile | null | undefined,
  shellRoles?: string[] | null,
): RoleUiMode {
  const mp = mentor != null;
  const mep = mentee != null;
  const jwtDefault = inferDashboardRoleFromJwt(shellRoles);

  if (mp && !mep) {
    return { defaultRole: "mentor", showRoleToggle: false };
  }
  if (mep && !mp) {
    return { defaultRole: "mentee", showRoleToggle: false };
  }
  if (mp && mep) {
    return { defaultRole: jwtDefault ?? "mentee", showRoleToggle: true };
  }
  return { defaultRole: jwtDefault ?? "mentee", showRoleToggle: false };
}
