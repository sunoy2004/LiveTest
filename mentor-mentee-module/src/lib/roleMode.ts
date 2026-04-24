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

/**
 * While GET /profile/full is loading. JWT and /me do not carry mentor/mentee flags;
 * roles are determined by mentor_profiles / mentee_profiles rows for this user id.
 */
export function getRoleUiModeWhileProfileLoading(): RoleUiMode {
  return { defaultRole: "mentee", showRoleToggle: false };
}

/**
 * Domain profiles are the source of truth for mentoring UI.
 * - Only mentor profile → mentor dashboard, no toggle
 * - Only mentee profile → mentee dashboard, no toggle
 * - Both → toggle, default mentee
 * - Neither → mentee UI, no toggle
 */
export function getRoleUiModeFromProfiles(
  mentor: UserServiceMentorProfile | null | undefined,
  mentee: UserServiceMenteeProfile | null | undefined,
): RoleUiMode {
  const mp = mentor != null;
  const mep = mentee != null;
  if (mp && !mep) {
    return { defaultRole: "mentor", showRoleToggle: false };
  }
  if (mep && !mp) {
    return { defaultRole: "mentee", showRoleToggle: false };
  }
  if (mp && mep) {
    return { defaultRole: "mentee", showRoleToggle: true };
  }
  return { defaultRole: "mentee", showRoleToggle: false };
}
