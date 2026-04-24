import * as React from "react";
import { useAuth } from "@/context/AuthContext";
import type { AuthUser } from "@/lib/auth";

const MENTOR_BASENAME = "/mentoring";

const MentorMenteeApp = React.lazy(() =>
  import("mentorMentee/App").then((m) => ({
    default: function MentorEmbedded({
      shellUser,
      shellToken,
    }: {
      shellUser: AuthUser | null;
      shellToken: string | null;
    }) {
      return (
        <m.default
          embedded
          basename={MENTOR_BASENAME}
          shellUser={shellUser}
          shellToken={shellToken}
        />
      );
    },
  })),
);

export function MentorMfeRemote() {
  const { user, token } = useAuth();
  return (
    <React.Suspense
      fallback={
        <div className="flex min-h-[12rem] flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
          <div className="h-8 w-8 animate-pulse rounded-lg bg-muted" />
          <span>Loading Mentoring…</span>
        </div>
      }
    >
      <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
        <MentorMenteeApp shellUser={user} shellToken={token} />
      </div>
    </React.Suspense>
  );
}
