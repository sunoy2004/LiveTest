import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { fetchProfileFull } from "@/api/userService";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";

/** Gate federated admin routes — requires User Service `is_admin`. */
export default function AdminAccess({ children }: { children: ReactNode }) {
  const { token, user } = useMentorShellAuth();

  const { data: fullProfile, isPending, isError } = useQuery({
    queryKey: ["user-service", "profile-full", token],
    queryFn: () => fetchProfileFull(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const isAdmin = Boolean(fullProfile?.is_admin ?? user?.is_admin);

  if (!token) {
    return <Navigate to="../.." replace />;
  }

  if (!isPending && (!isAdmin || isError)) {
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
