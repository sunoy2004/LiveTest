import { cn } from "@/lib/utils";
import { GraduationCap, Users } from "lucide-react";

interface RoleToggleProps {
  role: "mentor" | "mentee";
  onRoleChange: (role: "mentor" | "mentee") => void;
}

const RoleToggle = ({ role, onRoleChange }: RoleToggleProps) => {
  return (
    <div className="flex items-center rounded-full bg-muted p-1 gap-0.5 shadow-sm border border-border">
      <button
        onClick={() => onRoleChange("mentee")}
        className={cn(
          "flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300",
          role === "mentee"
            ? "gradient-primary text-primary-foreground shadow-md shadow-primary/25"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <GraduationCap className="h-4 w-4" />
        Mentee
      </button>
      <button
        onClick={() => onRoleChange("mentor")}
        className={cn(
          "flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300",
          role === "mentor"
            ? "gradient-primary text-primary-foreground shadow-md shadow-primary/25"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <Users className="h-4 w-4" />
        Mentor
      </button>
    </div>
  );
};

export default RoleToggle;
