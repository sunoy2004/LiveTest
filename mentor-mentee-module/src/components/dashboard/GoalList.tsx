import { Goal } from "@/data/mockData";
import { Target, CheckCircle, Zap, Trophy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface GoalListProps {
  goals: Goal[];
  emptyTitle?: string;
  emptySubtitle?: string;
}

const GoalList = ({ goals, emptyTitle, emptySubtitle }: GoalListProps) => {
  if (goals.length === 0) {
    return (
      <div className="text-center py-10 text-muted-foreground">
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
          <Trophy className="h-5 w-5 opacity-50" />
        </div>
        <p className="text-sm font-medium">{emptyTitle ?? "No quests active"}</p>
        <p className="text-xs mt-1">{emptySubtitle ?? "Start a learning quest to earn XP"}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {goals.map((goal, i) => {
        const isNearComplete = goal.progress >= 80;
        return (
          <div
            key={goal.id}
            className="group animate-fade-in"
            style={{ animationDelay: `${i * 80}ms`, animationFillMode: "backwards" }}
          >
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                {isNearComplete ? (
                  <CheckCircle className="h-4 w-4 text-success" />
                ) : (
                  <Target className="h-4 w-4 text-muted-foreground" />
                )}
                <p className="text-sm font-semibold text-foreground">{goal.title}</p>
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">{goal.category}</Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-0.5 text-[10px] font-bold text-primary">
                  <Zap className="h-3 w-3" /> {goal.xpReward} XP
                </span>
                <span className={cn(
                  "text-xs font-bold px-2 py-0.5 rounded-full",
                  isNearComplete
                    ? "bg-success/10 text-success"
                    : "bg-muted text-muted-foreground"
                )}>
                  {goal.progress}%
                </span>
              </div>
            </div>
            <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-700 ease-out",
                  isNearComplete ? "bg-success" : "gradient-primary"
                )}
                style={{ width: `${goal.progress}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default GoalList;
