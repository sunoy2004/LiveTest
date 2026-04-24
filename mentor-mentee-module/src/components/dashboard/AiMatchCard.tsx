import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, UserPlus, ThumbsDown, Loader2, Coins } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { MatchProfile } from "@/data/mockData";
import type { MentorTierId } from "@/types/domain";
import { cn } from "@/lib/utils";
import { postMentorshipRequest } from "@/lib/api/mentoring";
import { postRecommendationFeedback } from "@/lib/api/ai";
import { MentoringApiError } from "@/lib/api/client";
import { toast } from "@/hooks/use-toast";
import { qk } from "@/hooks/useMentoringQueries";
import { fetchMentorProfileDetail } from "@/api/userServiceMentoringApi";

const tierConfig: Record<
  MentorTierId,
  { label: string; className: string }
> = {
  PEER: { label: "Peer", className: "bg-muted text-muted-foreground" },
  PROFESSIONAL: { label: "Professional", className: "bg-primary/10 text-primary" },
  EXPERT: { label: "Expert", className: "bg-warning/10 text-warning" },
};

type Props = {
  match: MatchProfile;
  token: string | null;
  requestLocked?: boolean;
};

const DEFAULT_INTRO = "I'd like to request a mentorship connection with you.";

const AiMatchCard = ({ match, token, requestLocked }: Props) => {
  const qc = useQueryClient();
  const [profileOpen, setProfileOpen] = useState(false);
  const [connectOpen, setConnectOpen] = useState(false);
  const [intro, setIntro] = useState(DEFAULT_INTRO);
  const [busy, setBusy] = useState<"connect" | "reject" | null>(null);

  const tier = tierConfig[match.tier];
  const initials = match.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const mentorProfileId = match.mentorProfileId;
  const mentorUserId = match.mentorUserId ?? match.id;
  const canConnect = Boolean(mentorProfileId && token);

  const {
    data: mentorDetail,
    isFetching: mentorDetailLoading,
    isError: mentorDetailError,
  } = useQuery({
    queryKey: ["user-service", "mentor-profile-detail", mentorProfileId],
    queryFn: () => fetchMentorProfileDetail(token!, mentorProfileId!),
    enabled: Boolean(profileOpen && token && mentorProfileId),
    staleTime: 60_000,
  });

  const invalidateAi = () => void qc.invalidateQueries({ queryKey: qk.aiRecommendations });

  const handleNotInterested = async () => {
    if (!token || !mentorUserId) return;
    setBusy("reject");
    try {
      await postRecommendationFeedback({
        target_user_id: mentorUserId,
        interaction_type: "REJECTED_SUGGESTION",
      });
      toast({ title: "Updated", description: "We will show fewer suggestions like this." });
      invalidateAi();
    } catch (e) {
      const msg =
        e instanceof MentoringApiError
          ? String(e.message)
          : e instanceof Error
            ? e.message
            : "Request failed";
      toast({ title: "Could not save preference", description: msg, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const handleConnectSubmit = async () => {
    if (!token || !mentorProfileId) return;
    setBusy("connect");
    try {
      await postMentorshipRequest({
        mentor_id: mentorProfileId,
        intro_message: intro.trim() || DEFAULT_INTRO,
      });
      toast({ title: "Request sent", description: "The mentor will see your introduction." });
      setConnectOpen(false);
      setIntro(DEFAULT_INTRO);
      invalidateAi();
      void qc.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
    } catch (e) {
      const msg =
        e instanceof MentoringApiError
          ? String(e.message)
          : e instanceof Error
            ? e.message
            : "Request failed";
      toast({ title: "Connection request failed", description: msg, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <div
        className={cn(
          "group flex flex-col items-center text-center p-5 rounded-2xl border border-border bg-card",
          "hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-300",
          "relative overflow-hidden",
        )}
      >
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1 text-[10px] font-bold text-primary bg-primary/10 px-2 py-1 rounded-full">
          AI {match.aiMatchScore}%
        </div>
        <div
          className={cn(
            "absolute top-2.5 right-2.5 text-[10px] font-bold px-2 py-1 rounded-full",
            tier.className,
          )}
        >
          {tier.label}
        </div>

        <div className="relative mt-4">
          <div className="h-14 w-14 rounded-full gradient-primary flex items-center justify-center shadow-md shadow-primary/20 ring-2 ring-card">
            <span className="text-lg font-bold text-primary-foreground">{initials}</span>
          </div>
          <div
            className={cn(
              "absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full border-2 border-card",
              match.isAvailable ? "bg-success" : "bg-muted-foreground",
            )}
          />
        </div>

        <p className="font-semibold text-foreground text-sm mt-3">{match.name}</p>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{match.bio}</p>

        <div className="flex flex-wrap justify-center gap-1.5 mt-3">
          {match.skills.map((skill) => (
            <Badge key={skill} variant="secondary" className="text-[10px] font-medium px-2 py-0.5">
              {skill}
            </Badge>
          ))}
        </div>

        <div className="flex items-center gap-1 mt-3 text-xs text-muted-foreground">
          <Coins className="h-3 w-3" />
          <span className="font-semibold">{match.sessionCostCredits} credits</span>
          <span>/ session</span>
        </div>

        <div className="grid grid-cols-1 gap-2 w-full relative mt-3">
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={() => setProfileOpen(true)}
          >
            <Eye className="h-3 w-3 mr-1" /> View profile
          </Button>
          <Button
            size="sm"
            className="w-full text-xs gradient-primary border-0 shadow-sm shadow-primary/20"
            disabled={requestLocked || !canConnect || busy !== null}
            title={
              requestLocked
                ? "Guardian consent required"
                : !mentorProfileId
                  ? "Run AI reindex — mentor profile id missing"
                  : !token
                    ? "Sign in required"
                    : undefined
            }
            onClick={() => setConnectOpen(true)}
          >
            {busy === "connect" ? (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            ) : (
              <UserPlus className="h-3 w-3 mr-1" />
            )}
            Connect
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="w-full text-xs"
            disabled={!token || busy !== null}
            onClick={() => void handleNotInterested()}
          >
            {busy === "reject" ? (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            ) : (
              <ThumbsDown className="h-3 w-3 mr-1" />
            )}
            Not interested
          </Button>
        </div>
      </div>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{mentorDetail?.display_name ?? match.name}</DialogTitle>
            <DialogDescription>
              {mentorProfileId ? "Mentor profile details" : "AI-recommended mentor"}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-2 text-sm text-muted-foreground">
            {mentorProfileId ? (
              mentorDetailLoading ? (
                <div className="flex items-center gap-2 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading mentor profile…
                </div>
              ) : mentorDetailError ? (
                <p className="text-sm text-destructive">
                  Could not load mentor profile. Please try again.
                </p>
              ) : mentorDetail ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={cn("text-xs", tier.className)}>{tier.label}</Badge>
                    <span className="text-xs">
                      Tier: <span className="font-semibold text-foreground">{mentorDetail.mentor_profile.tier_id}</span>
                    </span>
                    <span className="text-xs">
                      Accepting requests:{" "}
                      <span className="font-semibold text-foreground">
                        {mentorDetail.mentor_profile.is_accepting_requests ? "Yes" : "No"}
                      </span>
                    </span>
                  </div>

                  {mentorDetail.mentor_profile.headline ? (
                    <p className="text-sm text-foreground">{mentorDetail.mentor_profile.headline}</p>
                  ) : null}

                  {mentorDetail.mentor_profile.current_title || mentorDetail.mentor_profile.current_company ? (
                    <p className="text-xs">
                      <span className="font-semibold text-foreground">Current:</span>{" "}
                      {[mentorDetail.mentor_profile.current_title, mentorDetail.mentor_profile.current_company]
                        .filter(Boolean)
                        .join(" @ ")}
                      {mentorDetail.mentor_profile.years_experience != null ? (
                        <>
                          {" "}
                          •{" "}
                          <span className="font-semibold text-foreground">
                            {mentorDetail.mentor_profile.years_experience}
                          </span>{" "}
                          yrs exp
                        </>
                      ) : null}
                    </p>
                  ) : null}

                  <div className="text-xs">
                    <span className="font-semibold text-foreground">Email:</span> {mentorDetail.email}
                  </div>

                  {mentorDetail.mentor_profile.bio ? (
                    <div>
                      <p className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">
                        About
                      </p>
                      <p className="text-sm leading-relaxed">{mentorDetail.mentor_profile.bio}</p>
                    </div>
                  ) : null}

                  <div>
                    <p className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">
                      Expertise areas
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {(mentorDetail.mentor_profile.expertise_areas ?? match.skills).map((s) => (
                        <Badge key={s} variant="secondary">
                          {s}
                        </Badge>
                      ))}
                      {(mentorDetail.mentor_profile.expertise_areas ?? match.skills).length === 0 ? (
                        <span className="text-xs">No expertise areas listed yet.</span>
                      ) : null}
                    </div>
                  </div>

                  <div className="text-xs">
                    Total hours mentored:{" "}
                    <span className="font-semibold text-foreground">
                      {mentorDetail.mentor_profile.total_hours_mentored}
                    </span>
                  </div>

                  {Array.isArray(mentorDetail.mentor_profile.professional_experiences) &&
                  mentorDetail.mentor_profile.professional_experiences.length ? (
                    <div>
                      <p className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2">
                        Experience
                      </p>
                      <ul className="space-y-2">
                        {mentorDetail.mentor_profile.professional_experiences.slice(0, 4).map((e, idx) => {
                          const title = String((e as any).title ?? "");
                          const company = String((e as any).company ?? "");
                          const summary = String((e as any).summary ?? "");
                          const years = (e as any).years;
                          const heading = [title, company].filter(Boolean).join(" @ ");
                          return (
                            <li key={idx} className="text-sm">
                              {heading ? <p className="text-foreground font-medium">{heading}</p> : null}
                              {years != null ? (
                                <p className="text-xs text-muted-foreground">{String(years)} yrs</p>
                              ) : null}
                              {summary ? <p className="text-sm">{summary}</p> : null}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ) : null}

                  <p className="text-xs">
                    Match score reflects semantic similarity between your goals and their profile.
                  </p>
                </>
              ) : (
                <p className="text-sm">No profile data.</p>
              )
            ) : (
              <>
                <p>{match.bio}</p>
                <div className="flex flex-wrap gap-1.5">
                  {match.skills.map((s) => (
                    <Badge key={s} variant="secondary">
                      {s}
                    </Badge>
                  ))}
                </div>
                <p className="text-xs">
                  Match score reflects semantic similarity between your goals and their expertise.
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={connectOpen} onOpenChange={setConnectOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect with {match.name}</DialogTitle>
            <DialogDescription>
              Sends a mentorship request (same as Workflow 1 — POST /api/v1/requests).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Textarea
              value={intro}
              onChange={(e) => setIntro(e.target.value)}
              rows={4}
              placeholder="Introduce yourself and what you hope to learn…"
              className="text-sm"
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setConnectOpen(false)}>
              Cancel
            </Button>
            <Button
              className="gradient-primary border-0"
              disabled={busy !== null || !canConnect}
              onClick={() => void handleConnectSubmit()}
            >
              {busy === "connect" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AiMatchCard;
