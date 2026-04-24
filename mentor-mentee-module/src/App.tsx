import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MentorShellAuthProvider } from "@/context/MentorShellAuthContext";
import type { ShellUser } from "@/types/shellAuth";
import AdminAccess from "./admin/AdminAccess.tsx";
import AdminLayout from "./admin/AdminLayout.tsx";
import AdminDisputesPage from "./admin/AdminDisputesPage.tsx";
import AdminMenteesPage from "./admin/AdminMenteesPage.tsx";
import AdminMentorsPage from "./admin/AdminMentorsPage.tsx";
import AdminSessionsPage from "./admin/AdminSessionsPage.tsx";
import Index from "./pages/Index.tsx";
import LeaderboardPage from "./pages/Leaderboard";
import NotFound from "./pages/NotFound.tsx";
import RoutesWrapper from "./RoutesWrapper.tsx";

const queryClient = new QueryClient();

function StandaloneRoutes() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="leaderboard" element={<LeaderboardPage />} />
      <Route
        path="admin/*"
        element={
          <AdminAccess>
            <AdminLayout />
          </AdminAccess>
        }
      >
        <Route index element={<Navigate to="mentors" replace />} />
        <Route path="mentors" element={<AdminMentorsPage />} />
        <Route path="mentees" element={<AdminMenteesPage />} />
        <Route path="sessions" element={<AdminSessionsPage />} />
        <Route path="disputes" element={<AdminDisputesPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export type MentorAppProps = {
  embedded?: boolean;
  /** Shell mount path when `embedded`; also passed to `BrowserRouter` when standalone. */
  basename?: string;
  /** Identity from common-ui-shell (User Service claims). */
  shellUser?: ShellUser | null;
  shellToken?: string | null;
};

/**
 * Standalone: `BrowserRouter` + root routes.
 * Federated: host owns the router — use `RoutesWrapper` so `/mentoring` matches `Index`.
 */
export default function App({
  embedded = false,
  basename = "/",
  shellUser = null,
  shellToken = null,
}: MentorAppProps) {
  const routerBasename = basename.replace(/\/$/, "") || "/";

  const routing = embedded ? (
    <RoutesWrapper basename={routerBasename} />
  ) : (
    <BrowserRouter basename={routerBasename === "/" ? undefined : routerBasename}>
      <StandaloneRoutes />
    </BrowserRouter>
  );

  return (
    <QueryClientProvider client={queryClient}>
      <MentorShellAuthProvider
        embedded={embedded}
        shellUser={shellUser}
        shellToken={shellToken}
      >
        <div
          data-mentor-mfe-root
          className={
            embedded
              ? "dark relative z-0 flex h-full min-h-0 min-w-0 w-full flex-1 flex-col overflow-auto pb-24 md:pb-32"
              : "dark min-h-screen w-full"
          }
        >
          <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
            <TooltipProvider>
              <Toaster />
              <Sonner />
              {routing}
            </TooltipProvider>
          </ThemeProvider>
        </div>
      </MentorShellAuthProvider>
    </QueryClientProvider>
  );
}
