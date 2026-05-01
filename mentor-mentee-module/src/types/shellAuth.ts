/** Mirrors User Service public user shape (identity + roles from `users.role`). */
/** Stored from /login and /me — `roles` mirrors JWT / DB (`MENTOR`, `MENTEE`, `ADMIN`); dashboard also uses mentoring profiles. */
export type ShellUser = {
  id: string;
  email: string;
  is_admin?: boolean;
  roles?: string[];
};
