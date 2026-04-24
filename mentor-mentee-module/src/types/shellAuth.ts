/** Mirrors User Service public user shape (identity only). */
/** Stored from /login and /me — identity + admin flag only; mentor/mentee come from profile tables. */
export type ShellUser = {
  id: string;
  email: string;
  is_admin?: boolean;
};
