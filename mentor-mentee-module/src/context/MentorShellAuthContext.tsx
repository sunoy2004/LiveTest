import * as React from "react";
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "@/lib/authStorage";
import type { ShellUser } from "@/types/shellAuth";

type MentorShellAuthValue = {
  user: ShellUser | null;
  token: string | null;
  embedded: boolean;
};

const MentorShellAuthContext = React.createContext<MentorShellAuthValue | null>(null);

type ProviderProps = {
  children: React.ReactNode;
  embedded: boolean;
  shellUser: ShellUser | null;
  shellToken: string | null;
};

/**
 * When embedded in common-ui-shell, identity comes from props (same React tree).
 * Standalone: read same localStorage keys as the shell so dev works without the host.
 */
export function MentorShellAuthProvider({
  children,
  embedded,
  shellUser,
  shellToken,
}: ProviderProps) {
  const [user, setUser] = React.useState<ShellUser | null>(shellUser);
  const [token, setToken] = React.useState<string | null>(shellToken);

  React.useEffect(() => {
    if (embedded) {
      setUser(shellUser);
      setToken(shellToken);
      return;
    }
    try {
      const t = localStorage.getItem(AUTH_TOKEN_KEY);
      const raw = localStorage.getItem(AUTH_USER_KEY);
      if (t && raw) {
        setToken(t);
        setUser(JSON.parse(raw) as ShellUser);
      } else {
        setToken(null);
        setUser(null);
      }
    } catch {
      setToken(null);
      setUser(null);
    }
  }, [embedded, shellUser, shellToken]);

  const value = React.useMemo(
    () => ({ user, token, embedded }),
    [user, token, embedded],
  );

  return (
    <MentorShellAuthContext.Provider value={value}>{children}</MentorShellAuthContext.Provider>
  );
}

export function useMentorShellAuth(): MentorShellAuthValue {
  const ctx = React.useContext(MentorShellAuthContext);
  if (!ctx) {
    throw new Error("useMentorShellAuth must be used within MentorShellAuthProvider");
  }
  return ctx;
}
