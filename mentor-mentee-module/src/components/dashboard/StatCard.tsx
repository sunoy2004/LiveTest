import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subtitle?: string;
  index?: number;
}

const StatCard = ({ icon: Icon, label, value, subtitle, index = 0 }: StatCardProps) => {
  return (
    <div
      className={cn(
        "group relative bg-card rounded-2xl p-5 shadow-card border border-border",
        "hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-300",
        "animate-slide-up overflow-hidden"
      )}
      style={{ animationDelay: `${index * 80}ms`, animationFillMode: "backwards" }}
    >
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-primary/[0.03] to-transparent pointer-events-none" />

      <div className="relative flex items-start gap-4">
        <div className="p-2.5 rounded-xl gradient-primary shadow-sm shadow-primary/20">
          <Icon className="h-5 w-5 text-primary-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-foreground mt-1 tracking-tight">{value}</p>
          {subtitle && (
            <p className="text-xs font-medium text-success mt-1.5 flex items-center gap-1">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-success" />
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
