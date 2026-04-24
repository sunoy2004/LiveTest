import RoleToggle from "./RoleToggle";
import { Sparkles } from "lucide-react";

interface DashboardHeaderProps {
  role: "mentor" | "mentee";
  onRoleChange: (role: "mentor" | "mentee") => void;
  /** When false, user has a single role from User Service — hide mentor/mentee switch. */
  showRoleToggle?: boolean;
  greetingName?: string;
}

const DashboardHeader = ({
  role,
  onRoleChange,
  showRoleToggle = true,
  greetingName = "there",
}: DashboardHeaderProps) => {
  return (
    <div className="flex flex-col gap-4 animate-fade-in sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground tracking-tight">
            Hello, {greetingName} 👋
          </h1>
          <Sparkles className="h-5 w-5 text-primary animate-pulse" />
        </div>
        <p className="text-muted-foreground text-sm md:text-base">
          Ready to grow today?
        </p>
      </div>
      {showRoleToggle ? <RoleToggle role={role} onRoleChange={onRoleChange} /> : null}
    </div>
  );
};

export default DashboardHeader;
