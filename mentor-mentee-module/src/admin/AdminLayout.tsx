import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  AlertTriangle,
  CalendarDays,
  GraduationCap,
  Network,
  Shield,
  UserCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdminRoot } from "./useAdminRoot";

const NAV = [
  { to: "mentors", label: "Mentors", icon: GraduationCap },
  { to: "mentees", label: "Mentees", icon: UserCircle },
  { to: "connections", label: "Connections", icon: Network },
  { to: "sessions", label: "Sessions", icon: CalendarDays },
  { to: "disputes", label: "Disputes", icon: AlertTriangle },
] as const;

export default function AdminLayout() {
  const adminRoot = useAdminRoot();
  const { pathname } = useLocation();

  return (
    <div className="dark flex min-h-0 w-full flex-1 flex-col gap-6 p-4 sm:p-6 md:p-8">
      <header className="space-y-1 border-b border-border pb-4">
        <div className="flex items-center gap-2 text-primary">
          <Shield className="h-6 w-6" />
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Admin</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Mentor tiers (PEER / PROFESSIONAL / EXPERT), connections, sessions, and disputes from the mentoring service.
          Wallets and ledger balances are managed by gamification — not here.
        </p>
      </header>

      <div
        role="status"
        className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200/90"
      >
        Wallet balances, credit grants, and deductions are handled by the <strong className="text-foreground">Gamification
        service</strong>. This admin UI only configures mentor session prices and views operational data.
      </div>

      <nav className="flex flex-wrap gap-2 border-b border-border pb-3" aria-label="Admin sections">
        {NAV.map(({ to, label, icon: Icon }) => {
          const href = `${adminRoot}/${to}`;
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <NavLink
              key={to}
              to={href}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              {label}
            </NavLink>
          );
        })}
      </nav>

      <div className="min-h-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
