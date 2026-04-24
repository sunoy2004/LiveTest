import { NavLink, useLocation } from "react-router-dom";
import { LayoutDashboard, GraduationCap, PanelLeft, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { UserMenu } from "./UserMenu";
import { useState, useMemo } from "react";
import { useAuth } from "@/context/AuthContext";

const dashboard = { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard } as const;
const mentoring = { to: "/mentoring", label: "Mentoring", icon: GraduationCap } as const;
const federatedAdmin = {
  to: "/mentoring/admin/mentors",
  label: "Admin",
  icon: Shield,
} as const;

export function AppSidebar() {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  /** Admins: Dashboard + federated Admin only (no duplicate Mentoring entry). Others: Dashboard + Mentoring. */
  const nav = useMemo(() => {
    if (user?.is_admin) {
      return [dashboard, federatedAdmin] as const;
    }
    return [dashboard, mentoring] as const;
  }, [user?.is_admin]);

  function isActive(to: string): boolean {
    if (to === "/dashboard") {
      return location.pathname === "/dashboard";
    }
    if (to === "/mentoring") {
      return (
        location.pathname === "/mentoring" ||
        (location.pathname.startsWith("/mentoring/") && !location.pathname.startsWith("/mentoring/admin"))
      );
    }
    if (to === "/mentoring/admin/mentors") {
      return location.pathname.startsWith("/mentoring/admin");
    }
    return location.pathname === to;
  }

  return (
    <aside
      className={cn(
        "flex h-full min-h-0 shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 ease-linear",
        collapsed ? "w-[4.25rem]" : "w-60",
      )}
    >
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border px-3">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="shrink-0 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <PanelLeft className="h-5 w-5" />
        </Button>
        {!collapsed && (
          <span className="truncate text-sm font-semibold tracking-tight">Common UI</span>
        )}
      </div>

      <nav
        className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2"
        aria-label="Main"
      >
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/dashboard"}
            className={() =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                collapsed && "justify-center px-2",
                isActive(to)
                  ? "bg-sidebar-accent text-sidebar-foreground"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/80 hover:text-sidebar-foreground",
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon className="h-5 w-5 shrink-0 opacity-90" aria-hidden />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <Separator className="shrink-0 bg-sidebar-border" />

      <div
        className={cn("shrink-0 bg-sidebar p-2", collapsed && "flex justify-center")}
      >
        <UserMenu collapsed={collapsed} />
      </div>
    </aside>
  );
}
