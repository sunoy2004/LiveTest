import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { fetchProfileFull } from "@/api/userService";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import { isAdminFromAccessToken } from "@/lib/jwtPayload";

/** Gate federated admin routes — requires User Service `is_admin` (from `GET /me` or JWT / shell). */
export default function AdminAccess({ children }: { children: ReactNode }) {
  const { token, user } = useMentorShellAuth();

  const { data: fullProfile, isPending } = useQuery({
    queryKey: ["user-service", "me", token],
    queryFn: () => fetchProfileFull(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const fromMe = fullProfile?.is_admin;
  const isAdmin =
    fromMe === true ||
    (fromMe === undefined && (Boolean(user?.is_admin) || isAdminFromAccessToken(token)));
  const deniedByServer = fromMe === false;

  if (!token) {
    return <Navigate to="../.." replace />;
  }

  if (!isPending && (deniedByServer || !isAdmin)) {
    return <Navigate to="../.." replace />;
  }

  if (isPending) {
    return (
      <div className="flex min-h-[12rem] items-center justify-center p-8 text-sm text-muted-foreground">
        Checking access…
      </div>
    );
  }

  return <>{children}</>;
}
