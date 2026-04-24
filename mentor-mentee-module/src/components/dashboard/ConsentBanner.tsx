import { ShieldAlert, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ConsentBannerProps {
  type: "consent" | "credits";
  className?: string;
}

const ConsentBanner = ({ type, className }: ConsentBannerProps) => {
  if (type === "consent") {
    return (
      <div className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/30 bg-warning/5",
        "animate-fade-in",
        className
      )}>
        <div className="p-2 rounded-lg bg-warning/10">
          <ShieldAlert className="h-4 w-4 text-warning" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground">Action Restricted: Guardian Consent Required</p>
          <p className="text-xs text-muted-foreground mt-0.5">Some features are locked until a guardian approves your account.</p>
        </div>
        <Button size="sm" variant="outline" className="text-xs border-warning/30 text-warning hover:bg-warning/10 shrink-0">
          <Lock className="h-3 w-3 mr-1" /> Request Consent
        </Button>
      </div>
    );
  }

  return (
    <div className={cn(
      "flex items-center gap-3 px-4 py-3 rounded-xl border border-destructive/30 bg-destructive/5",
      "animate-fade-in",
      className
    )}>
      <div className="p-2 rounded-lg bg-destructive/10">
        <Lock className="h-4 w-4 text-destructive" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground">Insufficient Credits</p>
        <p className="text-xs text-muted-foreground mt-0.5">You need more credits to book sessions. Earn or purchase credits to continue.</p>
      </div>
      <Button size="sm" className="text-xs gradient-primary border-0 shrink-0">
        Earn Credits
      </Button>
    </div>
  );
};

export default ConsentBanner;
