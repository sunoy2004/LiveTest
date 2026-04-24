import { MainRegion } from "@/components/layout/MainRegion";
import { BarChart3, Sparkles } from "lucide-react";
import { LeaderboardCard } from "@/components/dashboard/LeaderboardCard";

export function DashboardPage() {
  return (
    <MainRegion
      title="Dashboard"
      description="Overview and host metrics. Mentoring is loaded as a Module Federation remote (shared React runtime)."
    >
      <div className="animate-fade-in space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "Host status", value: "Running", icon: Sparkles },
            { label: "Environment", value: "Development", icon: BarChart3 },
            { label: "Mentoring", value: "Module Federation", icon: BarChart3 },
          ].map((card) => (
            <div
              key={card.label}
              className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
                  <card.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {card.label}
                  </p>
                  <p className="text-lg font-semibold text-foreground">{card.value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <LeaderboardCard />
          <div className="rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
            <p className="text-sm text-muted-foreground">
              This shell is independently deployable. The mentor remote exposes its UI via federation; mentor styles are
              scoped under <code className="text-foreground">data-mentor-mfe-root</code> to limit clashes with the host.
            </p>
          </div>
        </div>
      </div>
    </MainRegion>
  );
}
