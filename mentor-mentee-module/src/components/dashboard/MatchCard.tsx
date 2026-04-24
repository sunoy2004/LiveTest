import { useState } from "react";
import { MatchProfile } from "@/data/mockData";
import type { MentorTierId } from "@/types/domain";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { Eye, Send, Sparkles, Coins } from "lucide-react";

interface MatchCardProps {
  match: MatchProfile;
  onRequest?: (match: MatchProfile) => void;
  /** Workflow 1 — POST /requests returns 403 until guardian_consent_status is GRANTED */
  requestLocked?: boolean;
}

const tierConfig: Record<
  MentorTierId,
  { label: string; className: string }
> = {
  PEER: { label: "Peer", className: "bg-muted text-muted-foreground" },
  PROFESSIONAL: { label: "Professional", className: "bg-primary/10 text-primary" },
  EXPERT: { label: "Expert", className: "bg-warning/10 text-warning" },
};

const MatchCard = ({ match, onRequest, requestLocked }: MatchCardProps) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const initials = match.name.split(" ").map(n => n[0]).join("");
  const tier = tierConfig[match.tier];

  return (
    <>
      <div className={cn(
        "group flex flex-col items-center text-center p-5 rounded-2xl border border-border bg-card",
        "hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-300",
        "relative overflow-hidden"
      )}>
        {/* AI badge */}
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1 text-[10px] font-bold text-primary bg-primary/10 px-2 py-1 rounded-full">
          <Sparkles className="h-2.5 w-2.5" /> AI {match.aiMatchScore}%
        </div>

        {/* Tier badge */}
        <div className={cn("absolute top-2.5 right-2.5 text-[10px] font-bold px-2 py-1 rounded-full", tier.className)}>
          {tier.label}
        </div>

        {/* Hover gradient */}
        <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-primary/[0.03] to-transparent pointer-events-none" />

        <div className="relative mt-4">
          <div className="h-14 w-14 rounded-full gradient-primary flex items-center justify-center shadow-md shadow-primary/20 ring-2 ring-card">
            <span className="text-lg font-bold text-primary-foreground">{initials}</span>
          </div>
          <div className={cn(
            "absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full border-2 border-card",
            match.isAvailable ? "bg-success" : "bg-muted-foreground"
          )} />
        </div>

        <p className="font-semibold text-foreground text-sm mt-3">{match.name}</p>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{match.bio}</p>

        <div className="flex flex-wrap justify-center gap-1.5 mt-3">
          {match.skills.map((skill) => (
            <Badge key={skill} variant="secondary" className="text-[10px] font-medium px-2 py-0.5">
              {skill}
            </Badge>
          ))}
        </div>

        {/* Cost */}
        <div className="flex items-center gap-1 mt-3 text-xs text-muted-foreground">
          <Coins className="h-3 w-3" />
          <span className="font-semibold">{match.sessionCostCredits} credits</span>
          <span>/ session</span>
        </div>

        <div className="flex gap-2 w-full relative mt-3">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 text-xs"
            onClick={() => setProfileOpen(true)}
          >
            <Eye className="h-3 w-3 mr-1" /> Profile
          </Button>
          <Button
            size="sm"
            className="flex-1 text-xs gradient-primary border-0 shadow-sm shadow-primary/20"
            disabled={requestLocked}
            title={requestLocked ? "Guardian consent required (DPDP)" : undefined}
            onClick={() => onRequest?.(match)}
          >
            <Send className="h-3 w-3 mr-1" /> Request
          </Button>
        </div>
      </div>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Profile</DialogTitle>
            <DialogDescription>View full profile details</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center text-center gap-4 py-4">
            <div className="relative">
              <div className="h-20 w-20 rounded-full gradient-primary flex items-center justify-center shadow-lg shadow-primary/25">
                <span className="text-2xl font-bold text-primary-foreground">{initials}</span>
              </div>
              <div className={cn(
                "absolute -bottom-1 -right-1 h-5 w-5 rounded-full border-2 border-card",
                match.isAvailable ? "bg-success" : "bg-muted-foreground"
              )} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">{match.name}</h3>
              <div className="flex items-center justify-center gap-2 mt-1">
                <Badge className={cn("text-xs", tier.className)}>{tier.label}</Badge>
                <span className="flex items-center gap-1 text-xs text-primary font-bold">
                  <Sparkles className="h-3 w-3" /> {match.aiMatchScore}% Match
                </span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{match.bio}</p>
            <div>
              <p className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">Skills & Interests</p>
              <div className="flex flex-wrap justify-center gap-2">
                {match.skills.map((skill) => (
                  <Badge key={skill} variant="secondary">{skill}</Badge>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Coins className="h-4 w-4" />
              <span className="font-bold text-foreground">{match.sessionCostCredits} credits</span> per session
            </div>
            <Button
              className="w-full mt-2 gradient-primary border-0 shadow-md shadow-primary/25"
              disabled={requestLocked}
              onClick={() => { setProfileOpen(false); onRequest?.(match); }}
            >
              <Send className="h-4 w-4 mr-2" />
              Request Session with {match.name.split(" ")[0]}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MatchCard;
