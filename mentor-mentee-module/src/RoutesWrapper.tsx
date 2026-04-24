import { Navigate, Route, Routes } from "react-router-dom";
import AdminAccess from "./admin/AdminAccess.tsx";
import AdminLayout from "./admin/AdminLayout.tsx";
import AdminConnectionsPage from "./admin/AdminConnectionsPage.tsx";
import AdminDisputesPage from "./admin/AdminDisputesPage.tsx";
import AdminMenteesPage from "./admin/AdminMenteesPage.tsx";
import AdminMentorsPage from "./admin/AdminMentorsPage.tsx";
import AdminSessionsPage from "./admin/AdminSessionsPage.tsx";
import Index from "./pages/Index.tsx";
import LeaderboardPage from "./pages/Leaderboard";
import NotFound from "./pages/NotFound.tsx";

export type RoutesWrapperProps = {
  /** Host mount path, e.g. `/mentoring` (leading/trailing slashes tolerated). */
  basename: string;
};

function stripSlashes(path: string): string {
  return path.replace(/^\/+|\/+$/g, "");
}

function FederatedAppRoutes() {
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
        <Route path="connections" element={<AdminConnectionsPage />} />
        <Route path="sessions" element={<AdminSessionsPage />} />
        <Route path="disputes" element={<AdminDisputesPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

/**
 * Federated mode: the host owns `BrowserRouter`. Use `Routes` + `basename` so
 * `/mentoring/admin/mentors` matches `admin` → nested `mentors`.
 */
export default function RoutesWrapper({ basename }: RoutesWrapperProps) {
  const base = stripSlashes(basename);

  if (!base) {
    return <FederatedAppRoutes />;
  }

  const prefix = `/${base}`;

  return (
    <Routes basename={prefix}>
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
        <Route path="connections" element={<AdminConnectionsPage />} />
        <Route path="sessions" element={<AdminSessionsPage />} />
        <Route path="disputes" element={<AdminDisputesPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
