import * as React from "react";
import {
  AuthUser,
  clearAuth,
  getUserServiceBase,
  persistAuth,
  readStoredAuth,
} from "@/lib/auth";

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  isReady: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(null);
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [isReady, setIsReady] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      const { token: t, user: u } = readStoredAuth();
      if (!t) {
        setToken(null);
        setUser(null);
        setIsReady(true);
        return;
      }
      setToken(t);
      setUser(u);
      try {
        const res = await fetch(`${getUserServiceBase()}/me`, {
          headers: { Authorization: `Bearer ${t}` },
        });
        if (cancelled) return;
        if (res.ok) {
          const data = (await res.json()) as { user: AuthUser };
          persistAuth(t, data.user);
          setUser(data.user);
        } else {
          clearAuth();
          setToken(null);
          setUser(null);
        }
      } catch {
        if (cancelled) return;
        // User-service unreachable — keep cached session; APIs may fail until it is back.
      }
      if (!cancelled) setIsReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const logout = React.useCallback(() => {
    clearAuth();
    setToken(null);
    setUser(null);
  }, []);

  const refreshMe = React.useCallback(async () => {
    const { token: t } = readStoredAuth();
    if (!t) return;
    try {
      const res = await fetch(`${getUserServiceBase()}/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (!res.ok) {
        logout();
        return;
      }
      const data = (await res.json()) as { user: AuthUser };
      persistAuth(t, data.user);
      setUser(data.user);
    } catch {
      /* offline / user-service down — keep session */
    }
  }, [logout]);

  const login = React.useCallback(async (email: string, password: string): Promise<AuthUser> => {
    const res = await fetch(`${getUserServiceBase()}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const d = (err as { detail?: unknown }).detail;
      const msg =
        typeof d === "string"
          ? d
          : Array.isArray(d) && d[0] && typeof (d[0] as { msg?: string }).msg === "string"
            ? (d[0] as { msg: string }).msg
            : "Login failed";
      throw new Error(msg);
    }
    const data = (await res.json()) as {
      access_token: string;
    };
    
    // Decode JWT payload
    const token = data.access_token;
    const payloadBase64 = token.split(".")[1];
    const decodedPayload = JSON.parse(atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/"))) as {
      user_id?: string;
      email?: string;
      is_admin?: boolean;
      role?: unknown;
    };

    const rawRole = decodedPayload.role;
    const roles = Array.isArray(rawRole)
      ? rawRole.map((r) => String(r))
      : rawRole != null && rawRole !== ""
        ? [String(rawRole)]
        : [];

    const newUser: AuthUser = {
      id: String(decodedPayload.user_id ?? ""),
      email: String(decodedPayload.email ?? ""),
      is_admin: Boolean(decodedPayload.is_admin),
      roles,
    };

    persistAuth(token, newUser);
    setToken(token);
    setUser(newUser);
    return newUser;
  }, []);

  const value = React.useMemo(
    () => ({
      token,
      user,
      isReady,
      login,
      logout,
      refreshMe,
    }),
    [token, user, isReady, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
